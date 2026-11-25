"""Simulación de una jornada de reparto con un hilo por repartidor."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from paqueteria.concurrencia.central import CentralMonitoreo
from paqueteria.concurrencia.hilo_repartidor import HiloRepartidor
from paqueteria.excepciones.errores import PaqueteriaError
from paqueteria.modelo.repartidor import Repartidor
from paqueteria.util.reloj import Reloj


@dataclass(frozen=True)
class ResumenJornada:
    """Resultado de la jornada."""

    entregados: int = 0
    fallidos: int = 0
    devueltos: int = 0
    por_repartidor: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        lineas = [f"Entregados: {self.entregados}   Intentos fallidos: {self.fallidos}   "
                  f"Devueltos al remitente: {self.devueltos}"]
        for rid, n in sorted(self.por_repartidor.items()):
            lineas.append(f"  {rid}: {n} entrega(s)")
        return "\n".join(lineas)


class SimuladorJornada:
    """Lanza un HiloRepartidor por repartidor con envíos, muestra el avance y verifica el final."""

    def __init__(self, repartidores: list[Repartidor], central: CentralMonitoreo, reloj: Reloj,
                 prob_fallo: float = 0.10, semilla: int | None = None, pausa_max: float = 0.3):
        self._repartidores = [r for r in repartidores if r.envios()]
        self._central = central
        self._reloj = reloj
        self._prob_fallo = prob_fallo
        self._semilla = semilla
        self._pausa_max = pausa_max
        self._hilos: list[HiloRepartidor] = []

    def ejecutar(self) -> ResumenJornada:
        """Corre la jornada y regresa el resumen; los hilos trabajan al mismo tiempo."""
        if not self._repartidores:
            raise PaqueteriaError("Ningún repartidor tiene envíos asignados. Usa primero 'asignar'.")
        self._hilos = [
            HiloRepartidor(r, self._central, self._reloj, self._prob_fallo,
                           None if self._semilla is None else self._semilla + i, self._pausa_max)
            for i, r in enumerate(self._repartidores)]
        for hilo in self._hilos:
            hilo.start()
        while any(h.is_alive() for h in self._hilos):
            self._central.drenar()          # la central muestra el avance mientras ocurre
            time.sleep(0.05)
        for hilo in self._hilos:
            hilo.join()
        self._central.drenar()
        self._verificar_consistencia()
        entregados = fallidos = devueltos = 0
        por_repartidor = {}
        for hilo, rep in zip(self._hilos, self._repartidores):
            n = sum(1 for _, r in hilo.bitacora if r == "entregado")
            por_repartidor[rep.id] = n
            entregados += n
            fallidos += sum(1 for _, r in hilo.bitacora if r.startswith(("intento", "devuelto")))
            devueltos += sum(1 for _, r in hilo.bitacora if r.startswith("devuelto"))
        return ResumenJornada(entregados, fallidos, devueltos, por_repartidor)

    def _verificar_consistencia(self) -> None:
        """Revisa que el estado final de cada envío corresponda a lo que pasó en su hilo."""
        problemas = []
        for hilo in self._hilos:
            problemas.extend(hilo.errores)
            ultimo: dict[str, str] = {}
            for guia, resultado in hilo.bitacora:
                ultimo[guia] = resultado
            envios = {e.guia: e for e in hilo.envios_atendidos}
            for guia, resultado in ultimo.items():
                estado = envios[guia].estado.nombre
                esperado = ("Entregado" if resultado == "entregado"
                            else "Devuelto" if resultado.startswith("devuelto") else None)
                if esperado and estado != esperado:
                    problemas.append(f"{guia}: terminó {resultado} pero su estado es {estado}")
        if problemas:
            raise PaqueteriaError("La jornada quedó inconsistente:\n  " + "\n  ".join(problemas))

