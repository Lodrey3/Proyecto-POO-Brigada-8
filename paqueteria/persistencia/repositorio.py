"""Contrato de almacenamiento (patrón Repository)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from paqueteria.modelo.envio import Envio
from paqueteria.modelo.repartidor import Repartidor


class Repositorio(ABC):
    """Carga y guarda los datos del sistema; la lógica no sabe en qué formato."""

    @abstractmethod
    def cargar_envios(self) -> list[Envio]:
        """Regresa los envíos guardados, con su historial."""

    @abstractmethod
    def guardar_envios(self, envios: list[Envio]) -> None:
        """Guarda todos los envíos."""

    @abstractmethod
    def cargar_repartidores(self) -> list[Repartidor]:
        """Regresa los repartidores guardados (sin envíos: se reasignan al cargar)."""

    @abstractmethod
    def guardar_repartidores(self, reps: list[Repartidor]) -> None:
        """Guarda los repartidores."""

    @abstractmethod
    def cargar_contador(self) -> int:
        """Último número de guía usado."""

    @abstractmethod
    def guardar_contador(self, valor: int) -> None:
        """Guarda el último número de guía usado."""
