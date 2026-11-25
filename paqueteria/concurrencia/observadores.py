"""Observadores de la central: muestran o guardan el avance del reparto."""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod

from paqueteria.concurrencia.central import EventoAvance
from paqueteria.excepciones.errores import ArchivoError


class Observador(ABC):
    """Contrato de un observador: recibe cada evento de avance."""

    @abstractmethod
    def actualizar(self, evento: EventoAvance) -> None:
        """Reacciona a un evento."""


class VistaConsola(Observador):
    """Imprime el avance de cada repartidor; un Lock evita que se mezclen las líneas."""

    def __init__(self):
        self._lock = threading.Lock()

    def actualizar(self, evento: EventoAvance) -> None:
        with self._lock:
            print(f"  [{evento.fecha_hora:%H:%M}] {evento.repartidor_id}: {evento.guia} "
                  f"{evento.resultado:<28} entregados {evento.entregados}/{evento.total}",
                  flush=True)


class BitacoraArchivo(Observador):
    """Agrega cada evento a un archivo de texto."""

    def __init__(self, ruta: str):
        self._ruta = ruta
        self._lock = threading.Lock()
        try:
            carpeta = os.path.dirname(ruta)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
        except OSError as e:
            raise ArchivoError(f"No se pudo crear la carpeta de {ruta}: {e.strerror}") from None

    def actualizar(self, evento: EventoAvance) -> None:
        linea = (f"{evento.fecha_hora:%Y-%m-%d %H:%M};{evento.repartidor_id};{evento.guia};"
                 f"{evento.resultado};{evento.entregados}/{evento.total}\n")
        with self._lock:
            try:
                with open(self._ruta, "a", encoding="utf-8") as archivo:
                    archivo.write(linea)
            except OSError:
                pass  # La bitácora es auxiliar: si falla, el reparto continúa.
