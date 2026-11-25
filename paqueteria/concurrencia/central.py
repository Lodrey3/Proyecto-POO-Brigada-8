"""Central de monitoreo (patrón Observer, el «sujeto»)."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paqueteria.concurrencia.observadores import Observador


@dataclass(frozen=True)
class EventoAvance:
    """Aviso de un repartidor: qué pasó con una guía y cómo va su ruta."""

    repartidor_id: str
    guia: str
    resultado: str
    entregados: int
    total: int
    fecha_hora: datetime


class CentralMonitoreo:
    """Recibe los avisos de los hilos en una Queue y se los pasa a sus observadores.

    Los hilos solo llaman a publicar(); el hilo principal llama a drenar(), así
    los observadores nunca escriben al mismo tiempo.
    """

    def __init__(self):
        self._observadores: list[Observador] = []
        self._cola: queue.Queue[EventoAvance] = queue.Queue()
        self._lock = threading.Lock()

    def suscribir(self, obs: Observador) -> None:
        """Agrega un observador."""
        with self._lock:
            self._observadores.append(obs)

    def publicar(self, evento: EventoAvance) -> None:
        """Lo llaman los hilos: deja el evento en la cola (seguro entre hilos)."""
        self._cola.put(evento)

    def drenar(self) -> None:
        """Saca todos los eventos pendientes y avisa a cada observador."""
        while True:
            try:
                evento = self._cola.get_nowait()
            except queue.Empty:
                return
            with self._lock:
                observadores = list(self._observadores)
            for obs in observadores:
                obs.actualizar(evento)
