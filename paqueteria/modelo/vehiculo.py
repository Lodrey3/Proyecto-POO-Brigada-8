"""Vehículos de los repartidores."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Vehiculo(ABC):
    """Vehículo abstracto: lo único que importa es cuánto carga."""

    @abstractmethod
    def capacidad_kg(self) -> float:
        """Kilos máximos que puede llevar."""

    @abstractmethod
    def tipo(self) -> str:
        """Nombre del tipo de vehículo."""

    def __str__(self) -> str:
        return f"{self.tipo()} ({self.capacidad_kg():g} kg)"


class Motocicleta(Vehiculo):
    """Motocicleta: hasta 20 kg."""

    def capacidad_kg(self) -> float:
        return 20.0

    def tipo(self) -> str:
        return "motocicleta"


class Camioneta(Vehiculo):
    """Camioneta: hasta 500 kg."""

    def capacidad_kg(self) -> float:
        return 500.0

    def tipo(self) -> str:
        return "camioneta"
