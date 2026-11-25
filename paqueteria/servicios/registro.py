"""Registro en memoria de todos los envíos, indexados por guía."""

from __future__ import annotations

import threading
from datetime import date

from paqueteria.excepciones.errores import EnvioNoEncontradoError
from paqueteria.modelo.envio import Envio


class RegistroEnvios:
    """Guarda los envíos por guía; un RLock protege los accesos desde varios hilos."""

    def __init__(self):
        self._envios: dict[str, Envio] = {}
        self._lock = threading.RLock()

    def agregar(self, envio: Envio) -> None:
        """Agrega un envío que ya tiene guía."""
        with self._lock:
            self._envios[envio.guia] = envio

    def obtener(self, guia: str) -> Envio:
        """Regresa el envío; lanza EnvioNoEncontradoError si la guía no existe."""
        with self._lock:
            try:
                return self._envios[str(guia).strip().upper()]
            except KeyError:
                raise EnvioNoEncontradoError(f"No existe la guía {guia}") from None

    def en_almacen(self) -> list[Envio]:
        """Envíos en el almacén que todavía no tienen repartidor."""
        with self._lock:
            return [e for e in self._envios.values()
                    if e.estado.nombre == "EnAlmacen" and e.repartidor_id is None]

    def del_dia(self, fecha: date) -> list[Envio]:
        """Envíos registrados ese día o con algún movimiento ese día."""
        with self._lock:
            return [e for e in self._envios.values()
                    if any(r.fecha_hora.date() == fecha for r in e.historial())]

    def todos(self) -> list[Envio]:
        """Todos los envíos, en el orden en que se registraron."""
        with self._lock:
            return list(self._envios.values())
