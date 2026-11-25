"""Generador de números de guía únicos."""

from __future__ import annotations

import threading
from datetime import date


class GeneradorGuias:
    """Entrega guías PQ-AAAAMMDD-NNNN. El contador nunca se repite y se protege con un Lock."""

    def __init__(self, contador: int = 0):
        self._contador = contador
        self._lock = threading.Lock()

    @property
    def contador(self) -> int:
        """Último número entregado (se guarda entre ejecuciones)."""
        with self._lock:
            return self._contador

    def siguiente(self, fecha: date) -> str:
        """Regresa una guía nueva, por ejemplo PQ-20261120-0001."""
        with self._lock:
            self._contador += 1
            return f"PQ-{fecha:%Y%m%d}-{self._contador:04d}"
