"""Repartidores y los envíos que llevan."""

from __future__ import annotations

import threading

from paqueteria.excepciones.errores import CapacidadExcedidaError
from paqueteria.modelo.envio import Envio
from paqueteria.modelo.vehiculo import Vehiculo


class Repartidor:
    """Repartidor con un vehículo; su carga solo cambia con asignar() y retirar()."""

    def __init__(self, id: str, nombre: str, vehiculo: Vehiculo):
        self._id = id
        self._nombre = nombre
        self._vehiculo = vehiculo
        self._envios: list[Envio] = []
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        """Identificador, por ejemplo R01."""
        return self._id

    @property
    def nombre(self) -> str:
        """Nombre del repartidor."""
        return self._nombre

    @property
    def vehiculo(self) -> Vehiculo:
        """Vehículo que usa."""
        return self._vehiculo

    def envios(self) -> list[Envio]:
        """Copia de la lista de envíos asignados."""
        with self._lock:
            return list(self._envios)

    def carga_actual(self) -> float:
        """Kilos asignados."""
        with self._lock:
            return sum(e.peso_para_carga() for e in self._envios)

    def capacidad_disponible(self) -> float:
        """Kilos que todavía caben."""
        return self._vehiculo.capacidad_kg() - self.carga_actual()

    def puede_cargar(self, envio: Envio) -> bool:
        """Indica si el envío cabe."""
        return envio.peso_para_carga() <= self.capacidad_disponible() + 1e-9

    def asignar(self, envio: Envio) -> None:
        """Agrega el envío; lanza CapacidadExcedidaError si no cabe."""
        with self._lock:
            if not self.puede_cargar(envio):
                raise CapacidadExcedidaError(
                    f"{envio.guia} ({envio.peso_para_carga():g} kg) no cabe en la "
                    f"{self._vehiculo.tipo()} de {self._nombre}: "
                    f"quedan {self.capacidad_disponible():g} kg")
            self._envios.append(envio)
            envio.asignar_repartidor(self._id)

    def retirar(self, envio: Envio) -> None:
        """Quita un envío asignado (por ejemplo, si se cancela)."""
        with self._lock:
            if envio in self._envios:
                self._envios.remove(envio)
                envio.asignar_repartidor(None)

    def vaciar_ruta(self) -> list[Envio]:
        """Entrega la lista de envíos para repartir y libera la capacidad."""
        with self._lock:
            ruta, self._envios = self._envios, []
            return ruta

    def __str__(self) -> str:
        return (f"{self._id}  {self._nombre:<18} {str(self._vehiculo):<22} "
                f"carga {self.carga_actual():g}/{self._vehiculo.capacidad_kg():g} kg, "
                f"{len(self._envios)} envío(s)")
