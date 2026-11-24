"""Estados de un envío (patrón State).

Cada estado sabe qué acciones permite. Las acciones que un estado no redefine
se rechazan con una excepción, así no hacen falta cadenas de if/elif sobre el
estado del envío. Los estados no guardan datos, por eso se comparten entre
todos los envíos.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from paqueteria.excepciones.errores import (
    CancelacionNoPermitidaError,
    DatoInvalidoError,
    TransicionInvalidaError,
)

if TYPE_CHECKING:
    from paqueteria.modelo.envio import Envio

MAX_INTENTOS = 3


class EstadoEnvio:
    """Estado abstracto: por defecto rechaza todas las acciones."""

    nombre = "Estado"

    def _rechazar(self, accion: str) -> None:
        raise TransicionInvalidaError(
            f"No se puede {accion}: el envío está en estado {self.nombre}")

    def ingresar_a_almacen(self, envio: Envio, fecha: datetime) -> None:
        """Pasa el envío al almacén."""
        self._rechazar("ingresar al almacén")

    def salir_a_ruta(self, envio: Envio, fecha: datetime) -> None:
        """Saca el envío del almacén para repartirlo."""
        self._rechazar("salir a ruta")

    def entregar(self, envio: Envio, fecha: datetime) -> None:
        """Registra la entrega al destinatario."""
        self._rechazar("entregar")

    def registrar_intento_fallido(self, envio: Envio, fecha: datetime) -> None:
        """Registra que el destinatario no estaba."""
        self._rechazar("registrar un intento fallido")

    def cancelar(self, envio: Envio, fecha: datetime) -> None:
        """Cancela el envío. Por defecto no se permite."""
        raise CancelacionNoPermitidaError(
            f"No se puede cancelar: el envío está en estado {self.nombre}. "
            "Solo se cancela antes de salir a ruta.")

    def es_final(self) -> bool:
        """Indica si el envío ya no puede cambiar de estado."""
        return False

    @staticmethod
    def desde_nombre(nombre: str) -> EstadoEnvio:
        """Regresa el estado con ese nombre (se usa al cargar los archivos)."""
        try:
            return _ESTADOS[nombre]
        except KeyError:
            raise DatoInvalidoError("estado", f"'{nombre}' no es un estado válido") from None

    def __str__(self) -> str:
        return self.nombre


class EstadoRegistrado(EstadoEnvio):
    """El envío se registró y aún no llega al almacén."""

    nombre = "Registrado"

    def ingresar_a_almacen(self, envio: Envio, fecha: datetime) -> None:
        envio._cambiar_estado(EN_ALMACEN, fecha, "Recibido en almacén")

    def cancelar(self, envio: Envio, fecha: datetime) -> None:
        envio._cambiar_estado(CANCELADO, fecha, "Cancelado antes de llegar al almacén")


class EstadoEnAlmacen(EstadoEnvio):
    """El envío está en el almacén esperando repartidor."""

    nombre = "EnAlmacen"

    def salir_a_ruta(self, envio: Envio, fecha: datetime) -> None:
        envio._cambiar_estado(EN_RUTA, fecha, "Salió a ruta")

    def cancelar(self, envio: Envio, fecha: datetime) -> None:
        envio._cambiar_estado(CANCELADO, fecha, "Cancelado en almacén")


class EstadoEnRuta(EstadoEnvio):
    """El repartidor lleva el envío al destinatario."""

    nombre = "EnRuta"

    def entregar(self, envio: Envio, fecha: datetime) -> None:
        envio._cambiar_estado(ENTREGADO, fecha, "Entregado al destinatario")

    def registrar_intento_fallido(self, envio: Envio, fecha: datetime) -> None:
        intentos = envio._incrementar_intentos()
        if intentos < MAX_INTENTOS:
            envio._cambiar_estado(
                EN_ALMACEN, fecha,
                f"Intento fallido {intentos} de {MAX_INTENTOS}; regresa al almacén")
        else:
            envio._cambiar_estado(
                DEVUELTO, fecha,
                f"Intento fallido {intentos} de {MAX_INTENTOS}; se devuelve al remitente")


class EstadoEntregado(EstadoEnvio):
    """Estado final: el destinatario recibió el envío."""

    nombre = "Entregado"

    def es_final(self) -> bool:
        return True


class EstadoDevuelto(EstadoEnvio):
    """Estado final: se devolvió al remitente tras tres intentos fallidos."""

    nombre = "Devuelto"

    def es_final(self) -> bool:
        return True


class EstadoCancelado(EstadoEnvio):
    """Estado final: el envío se canceló antes de salir a ruta."""

    nombre = "Cancelado"

    def es_final(self) -> bool:
        return True


REGISTRADO = EstadoRegistrado()
EN_ALMACEN = EstadoEnAlmacen()
EN_RUTA = EstadoEnRuta()
ENTREGADO = EstadoEntregado()
DEVUELTO = EstadoDevuelto()
CANCELADO = EstadoCancelado()

_ESTADOS = {e.nombre: e for e in (REGISTRADO, EN_ALMACEN, EN_RUTA, ENTREGADO, DEVUELTO, CANCELADO)}
