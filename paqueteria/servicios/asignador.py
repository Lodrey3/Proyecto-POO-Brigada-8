"""Asignación de los envíos del almacén a los repartidores."""

from __future__ import annotations

from dataclasses import dataclass, field

from paqueteria.excepciones.errores import CapacidadExcedidaError
from paqueteria.modelo.envio import Envio
from paqueteria.modelo.repartidor import Repartidor


@dataclass(frozen=True)
class ResultadoAsignacion:
    """Qué guías recibió cada repartidor y cuáles no cupieron."""

    asignados: dict[str, list[str]] = field(default_factory=dict)
    sin_asignar: list[str] = field(default_factory=list)


class AsignadorEnvios:
    """Reparte envíos sin exceder la capacidad (first-fit decreasing por peso)."""

    def asignar(self, envios: list[Envio], repartidores: list[Repartidor]) -> ResultadoAsignacion:
        """Acomoda primero los más pesados, cada uno en el primer repartidor donde quepa."""
        asignados: dict[str, list[str]] = {r.id: [] for r in repartidores}
        sin_asignar: list[str] = []
        for envio in sorted(envios, key=lambda e: e.peso_para_carga(), reverse=True):
            for repartidor in repartidores:
                if repartidor.puede_cargar(envio):
                    try:
                        repartidor.asignar(envio)
                    except CapacidadExcedidaError:
                        continue
                    asignados[repartidor.id].append(envio.guia)
                    break
            else:
                sin_asignar.append(envio.guia)
        return ResultadoAsignacion({k: v for k, v in asignados.items() if v}, sin_asignar)
