"""Hilo que recorre la ruta de un repartidor durante la simulación."""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from paqueteria.concurrencia.central import CentralMonitoreo, EventoAvance
from paqueteria.excepciones.errores import PaqueteriaError
from paqueteria.modelo.envio import Envio
from paqueteria.modelo.repartidor import Repartidor
from paqueteria.util.reloj import Reloj


class HiloRepartidor(threading.Thread):
    """Un hilo por repartidor. Solo toca los envíos de su repartidor.

    Cada intento tarda un tiempo aleatorio y falla con probabilidad ``prob_fallo``.
    Un envío con intento fallido vuelve al almacén y se reintenta al final de la
    ruta, hasta entregarlo o devolverlo al remitente al tercer intento.
    """

    def __init__(self, repartidor: Repartidor, central: CentralMonitoreo, reloj: Reloj,
                 prob_fallo: float, semilla: int | None = None, pausa_max: float = 0.3):
        super().__init__(name=f"Hilo-{repartidor.id}")
        self._repartidor = repartidor
        self._central = central
        self._reloj = reloj
        self._prob_fallo = prob_fallo
        self._azar = random.Random(semilla)
        self._pausa_max = pausa_max
        self._minutos = 0
        self._inicio: datetime | None = None
        self.bitacora: list[tuple[str, str]] = []   # (guía, resultado) en orden
        self.errores: list[str] = []
        self.envios_atendidos: list[Envio] = []
        self._entregados = 0
        self._total = 0

    def run(self) -> None:
        """Recorre la ruta hasta que todos los envíos terminan entregados o devueltos."""
        ruta = deque(self._repartidor.vaciar_ruta())
        self.envios_atendidos = list(ruta)
        self._total = len(ruta)
        ultimo = max((e.historial()[-1].fecha_hora for e in ruta), default=self._reloj.ahora())
        self._inicio = max(self._reloj.ahora(), ultimo)
        try:
            while ruta:
                envio = ruta.popleft()
                if self._atender(envio):
                    ruta.append(envio)
        except Exception as e:  # un error inesperado no debe mostrar traceback desde el hilo
            self.errores.append(f"error inesperado en {self.name}: {e}")

    def _fecha(self) -> datetime:
        """Hora simulada del hilo: avanza entre 5 y 20 minutos por intento."""
        self._minutos += self._azar.randint(5, 20)
        return self._inicio + timedelta(minutes=self._minutos)

    def _atender(self, envio: Envio) -> bool:
        """Intenta entregar; regresa True si el envío volvió al almacén y hay que reintentarlo."""
        try:
            envio.salir_a_ruta(self._fecha())
            time.sleep(self._azar.uniform(0.02, self._pausa_max))
            if self._azar.random() < self._prob_fallo:
                envio.registrar_intento_fallido(self._fecha())
                if envio.estado.nombre == "Devuelto":
                    resultado, reintentar = "devuelto al remitente (3/3)", False
                else:
                    resultado = f"intento fallido ({envio.intentos_fallidos}/3)"
                    reintentar = True
            else:
                envio.entregar(self._fecha())
                self._entregados += 1
                resultado, reintentar = "entregado", False
        except PaqueteriaError as e:
            self.errores.append(f"{envio.guia}: {e}")
            resultado, reintentar = f"error: {e}", False
        self.bitacora.append((envio.guia, resultado))
        self._central.publicar(EventoAvance(self._repartidor.id, envio.guia, resultado,
                                            self._entregados, self._total,
                                            envio.historial()[-1].fecha_hora))
        return reintentar
