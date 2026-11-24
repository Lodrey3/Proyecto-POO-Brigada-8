"""Servicios de entrega (patrón Strategy): estándar y express son intercambiables."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Servicio(ABC):
    """Contrato de un servicio de entrega: precio relativo y días de entrega."""

    @abstractmethod
    def nombre(self) -> str:
        """Nombre que se muestra al usuario."""

    @abstractmethod
    def factor_precio(self) -> float:
        """Multiplicador que se aplica al precio (1.0 = sin recargo)."""

    @abstractmethod
    def dias_min(self) -> int:
        """Mínimo de días de entrega."""

    @abstractmethod
    def dias_max(self) -> int:
        """Máximo de días de entrega."""

    def es_express(self) -> bool:
        """Indica si el servicio es express (lo consulta el paquete refrigerado)."""
        return False

    def __str__(self) -> str:
        return self.nombre()


class ServicioEstandar(Servicio):
    """Servicio estándar: de 3 a 5 días, sin recargo."""

    def nombre(self) -> str:
        return "Estándar"

    def factor_precio(self) -> float:
        return 1.0

    def dias_min(self) -> int:
        return 3

    def dias_max(self) -> int:
        return 5


class ServicioExpress(Servicio):
    """Servicio express: al día siguiente, 50 % más caro."""

    def nombre(self) -> str:
        return "Express"

    def factor_precio(self) -> float:
        return 1.5

    def dias_min(self) -> int:
        return 1

    def dias_max(self) -> int:
        return 1

    def es_express(self) -> bool:
        return True
