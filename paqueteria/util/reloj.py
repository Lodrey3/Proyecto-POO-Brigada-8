"""Relojes del sistema.

Toda operación que depende de la fecha pide la hora a un Reloj. Así las reglas
de fecha se pueden probar fijando la fecha y la hora desde la terminal
(``--fecha-hora``) sin esperar a que ocurran.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class Reloj(ABC):
    """Contrato de un reloj: solo sabe decir qué hora es."""

    @abstractmethod
    def ahora(self) -> datetime:
        """Regresa la fecha y hora actuales según este reloj."""


class RelojSistema(Reloj):
    """Reloj que entrega la hora real de la computadora."""

    def ahora(self) -> datetime:
        """Regresa la hora real, sin segundos ni microsegundos."""
        return datetime.now().replace(second=0, microsecond=0)


class RelojSimulado(Reloj):
    """Reloj con una hora fija que se puede cambiar o avanzar a mano."""

    def __init__(self, instante: datetime):
        self._instante = instante
        self._lock = threading.Lock()

    def ahora(self) -> datetime:
        """Regresa la hora fijada."""
        with self._lock:
            return self._instante

    def fijar(self, instante: datetime) -> None:
        """Cambia la hora del reloj."""
        with self._lock:
            self._instante = instante

    def avanzar(self, delta: timedelta) -> None:
        """Adelanta el reloj la cantidad indicada."""
        with self._lock:
            self._instante += delta
