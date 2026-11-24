"""Tipos de envío: sobre, paquete, paquete frágil y paquete refrigerado.

``Envio.cotizar()`` es un Template Method: fija el orden del cálculo y cada
subclase redefine solo su parte (costo base, recargo o seguro).
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from paqueteria.excepciones.errores import DatoInvalidoError, EnvioNoPermitidoError
from paqueteria.modelo.contacto import Contacto
from paqueteria.modelo.estados import REGISTRADO, EstadoEnvio
from paqueteria.modelo.servicio import Servicio
from paqueteria.modelo.valores import Cotizacion, Dimensiones, RegistroEstado, Zona

if TYPE_CHECKING:
    from paqueteria.modelo.tarifas import TablaTarifas


class Envio(ABC):
    """Envío abstracto: datos comunes, cálculo del precio y cambios de estado."""

    def __init__(self, remitente: Contacto, destinatario: Contacto, zona: Zona,
                 servicio: Servicio, fecha_registro: datetime):
        self._guia: str | None = None
        self._remitente = remitente
        self._destinatario = destinatario
        self._zona = zona
        self._servicio = servicio
        self._estado: EstadoEnvio = REGISTRADO
        self._historial: list[RegistroEstado] = []
        self._intentos_fallidos = 0
        self._repartidor_id: str | None = None
        self._fecha_registro = fecha_registro
        self._cotizacion: Cotizacion | None = None
        self._lock = threading.RLock()

    # ----- datos de solo lectura -------------------------------------------
    @property
    def guia(self) -> str | None:
        """Número de guía; None mientras no se registra."""
        return self._guia

    @property
    def remitente(self) -> Contacto:
        """Quien envía."""
        return self._remitente

    @property
    def destinatario(self) -> Contacto:
        """Quien recibe."""
        return self._destinatario

    @property
    def zona(self) -> Zona:
        """Zona de destino."""
        return self._zona

    @property
    def servicio(self) -> Servicio:
        """Servicio contratado (estándar o express)."""
        return self._servicio

    @property
    def estado(self) -> EstadoEnvio:
        """Estado actual."""
        return self._estado

    @property
    def intentos_fallidos(self) -> int:
        """Cuántas veces no estuvo el destinatario."""
        return self._intentos_fallidos

    @property
    def repartidor_id(self) -> str | None:
        """Repartidor al que se asignó, si hay."""
        return self._repartidor_id

    @property
    def fecha_registro(self) -> datetime:
        """Fecha y hora en que se capturó el envío."""
        return self._fecha_registro

    @property
    def cotizacion(self) -> Cotizacion | None:
        """Última cotización calculada."""
        return self._cotizacion

    # ----- validación y precio (Template Method) ---------------------------
    def validar(self) -> None:
        """Revisa los contactos y las reglas propias del tipo de envío."""
        self._remitente.validar("remitente")
        self._destinatario.validar("destinatario")
        self._validar_reglas()

    def cotizar(self, tarifas: TablaTarifas) -> Cotizacion:
        """Calcula el precio, lo guarda en el envío y lo regresa.

        Orden: base -> recargo del tipo -> factor del servicio -> seguro.
        El seguro se suma al final y no recibe el recargo express.
        """
        base = self._costo_base(tarifas)
        recargo = self._recargo(base)
        recargo_servicio = (base + recargo) * (self._servicio.factor_precio() - 1)
        seguro = self._seguro()
        total = base + recargo + recargo_servicio + seguro
        self._cotizacion = Cotizacion(
            base=round(base, 2), recargo_fragil=round(recargo, 2),
            recargo_servicio=round(recargo_servicio, 2), seguro=round(seguro, 2),
            total=round(total, 2), dias_min=self._servicio.dias_min(),
            dias_max=self._servicio.dias_max())
        return self._cotizacion

    def total(self) -> float:
        """Total de la última cotización (0 si nunca se cotizó)."""
        return self._cotizacion.total if self._cotizacion else 0.0

    @abstractmethod
    def _costo_base(self, tarifas: TablaTarifas) -> float:
        """Precio antes de recargos; cada tipo lo calcula a su manera."""

    def _validar_reglas(self) -> None:
        """Gancho para reglas extra del tipo; por defecto no exige nada."""

    def _recargo(self, base: float) -> float:
        """Recargo propio del tipo; por defecto no hay."""
        return 0.0

    def _seguro(self) -> float:
        """Seguro obligatorio; por defecto no hay."""
        return 0.0

    @abstractmethod
    def peso_para_carga(self) -> float:
        """Kilos que ocupa en el vehículo (peso real)."""

    @abstractmethod
    def tipo(self) -> str:
        """Nombre del tipo de envío."""

    # ----- ciclo de vida (delegado al patrón State) ------------------------
    def asignar_guia(self, guia: str) -> None:
        """Pone la guía y anota el registro en el historial. Solo se hace una vez."""
        with self._lock:
            if self._guia is not None:
                raise EnvioNoPermitidoError(f"El envío ya tiene la guía {self._guia}")
            self._guia = guia
            self._historial.append(RegistroEstado(REGISTRADO.nombre, self._fecha_registro,
                                                  "Envío registrado"))

    def asignar_repartidor(self, repartidor_id: str | None) -> None:
        """Anota (o quita, con None) el repartidor que llevará el envío."""
        with self._lock:
            self._repartidor_id = repartidor_id

    def ingresar_a_almacen(self, fecha: datetime) -> None:
        """Recibe el envío en el almacén."""
        with self._lock:
            self._estado.ingresar_a_almacen(self, fecha)

    def salir_a_ruta(self, fecha: datetime) -> None:
        """Saca el envío a reparto."""
        with self._lock:
            self._estado.salir_a_ruta(self, fecha)

    def entregar(self, fecha: datetime) -> None:
        """Registra la entrega."""
        with self._lock:
            self._estado.entregar(self, fecha)

    def registrar_intento_fallido(self, fecha: datetime) -> None:
        """Registra que el destinatario no estaba."""
        with self._lock:
            self._estado.registrar_intento_fallido(self, fecha)

    def cancelar(self, fecha: datetime) -> None:
        """Cancela el envío si aún no sale a ruta."""
        with self._lock:
            self._estado.cancelar(self, fecha)

    def historial(self) -> tuple[RegistroEstado, ...]:
        """Copia de solo lectura del historial de cambios."""
        with self._lock:
            return tuple(self._historial)

    def _cambiar_estado(self, nuevo: EstadoEnvio, fecha: datetime, nota: str) -> None:
        """Cambia el estado y agrega la entrada al historial (lo llaman los estados)."""
        if self._historial and fecha < self._historial[-1].fecha_hora:
            raise DatoInvalidoError(
                "fecha", f"{fecha:%Y-%m-%d %H:%M} es anterior al último movimiento "
                         f"({self._historial[-1].fecha_hora:%Y-%m-%d %H:%M})")
        self._estado = nuevo
        self._historial.append(RegistroEstado(nuevo.nombre, fecha, nota))

    def _incrementar_intentos(self) -> int:
        """Suma un intento fallido y regresa cuántos van."""
        self._intentos_fallidos += 1
        return self._intentos_fallidos

    def restaurar(self, guia: str, estado: EstadoEnvio, historial: list[RegistroEstado],
                  intentos_fallidos: int, repartidor_id: str | None,
                  cotizacion: Cotizacion | None) -> None:
        """Repone los datos guardados en archivo. Solo lo usa la persistencia."""
        with self._lock:
            self._guia = guia
            self._estado = estado
            self._historial = list(historial)
            self._intentos_fallidos = intentos_fallidos
            self._repartidor_id = repartidor_id
            self._cotizacion = cotizacion

    def __str__(self) -> str:
        guia = self._guia or "(sin guía)"
        return (f"{guia}  {self.tipo():<20} {self._servicio.nombre():<9} "
                f"{str(self._zona):<9} {self._estado.nombre:<10} ${self.total():>9,.2f}  "
                f"-> {self._destinatario}")


class Sobre(Envio):
    """Sobre: tarifa fija según la zona."""

    PESO_KG = 0.1

    def _costo_base(self, tarifas: TablaTarifas) -> float:
        return tarifas.tarifa_sobre(self._zona)

    def peso_para_carga(self) -> float:
        return self.PESO_KG

    def tipo(self) -> str:
        return "Sobre"


class Paquete(Envio):
    """Paquete: se cobra por kilo usando el mayor entre peso real y volumétrico."""

    def __init__(self, remitente: Contacto, destinatario: Contacto, zona: Zona,
                 servicio: Servicio, fecha_registro: datetime, peso_kg: float,
                 dimensiones: Dimensiones, valor_declarado: float):
        super().__init__(remitente, destinatario, zona, servicio, fecha_registro)
        self._peso_kg = peso_kg
        self._dimensiones = dimensiones
        self._valor_declarado = valor_declarado

    @property
    def peso_kg(self) -> float:
        """Peso real en kilos."""
        return self._peso_kg

    @property
    def dimensiones(self) -> Dimensiones:
        """Medidas en centímetros."""
        return self._dimensiones

    @property
    def valor_declarado(self) -> float:
        """Valor del contenido según el remitente."""
        return self._valor_declarado

    def peso_volumetrico(self) -> float:
        """Peso volumétrico en kilos."""
        return self._dimensiones.peso_volumetrico_kg()

    def peso_cobrado(self) -> float:
        """El mayor entre el peso real y el volumétrico."""
        return max(self._peso_kg, self.peso_volumetrico())

    def _costo_base(self, tarifas: TablaTarifas) -> float:
        return self.peso_cobrado() * tarifas.tarifa_kg(self._zona)

    def _validar_reglas(self) -> None:
        if self._peso_kg <= 0:
            raise DatoInvalidoError("peso_kg", "debe ser mayor que 0")
        d = self._dimensiones
        if min(d.largo_cm, d.ancho_cm, d.alto_cm) <= 0:
            raise DatoInvalidoError("medidas", "largo, ancho y alto deben ser mayores que 0")
        if self._valor_declarado <= 0:
            raise DatoInvalidoError("valor_declarado", "debe ser mayor que 0")

    def peso_para_carga(self) -> float:
        return self._peso_kg

    def tipo(self) -> str:
        return "Paquete"


class PaqueteFragil(Paquete):
    """Paquete frágil: 20 % adicional y seguro obligatorio del 3 % del valor declarado."""

    RECARGO = 0.20
    SEGURO = 0.03

    def _recargo(self, base: float) -> float:
        return base * self.RECARGO

    def _seguro(self) -> float:
        return self._valor_declarado * self.SEGURO

    def tipo(self) -> str:
        return "Paquete frágil"


class PaqueteRefrigerado(Paquete):
    """Paquete refrigerado: solo por express y nunca a la zona nacional."""

    def _validar_reglas(self) -> None:
        super()._validar_reglas()
        if not self._servicio.es_express():
            raise EnvioNoPermitidoError("Un paquete refrigerado solo puede enviarse por express")
        if self._zona is Zona.NACIONAL:
            raise EnvioNoPermitidoError("Un paquete refrigerado no puede ir a la zona nacional")

    def tipo(self) -> str:
        return "Paquete refrigerado"

