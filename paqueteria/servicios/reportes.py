"""Reporte diario: se calcula (ReporteDiario) y se escribe por separado."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from paqueteria.excepciones.errores import ArchivoError
from paqueteria.modelo.envio import Envio


@dataclass(frozen=True)
class ReporteDiario:
    """Números del día: envíos por estado, ingresos y entregas por repartidor."""

    fecha: date
    por_estado: dict[str, int] = field(default_factory=dict)
    ingresos_por_tipo: dict[str, float] = field(default_factory=dict)
    ingresos_por_servicio: dict[str, float] = field(default_factory=dict)
    entregas_por_repartidor: dict[str, int] = field(default_factory=dict)

    def texto(self) -> str:
        """Reporte listo para imprimir o guardar."""
        def bloque(titulo, datos, dinero=False):
            lineas = [titulo]
            if not datos:
                lineas.append("  (sin datos)")
            for clave, valor in sorted(datos.items()):
                lineas.append(f"  {clave:<22} ${valor:>11,.2f}" if dinero else f"  {clave:<22} {valor:>6}")
            if dinero and datos:
                lineas.append(f"  {'TOTAL':<22} ${sum(datos.values()):>11,.2f}")
            return "\n".join(lineas)

        return "\n\n".join([
            f"REPORTE DIARIO DE PAQUETERÍA - {self.fecha:%Y-%m-%d}",
            bloque("Envíos por estado actual (con movimiento ese día):", self.por_estado),
            bloque("Ingresos por tipo de envío (registrados ese día):", self.ingresos_por_tipo, True),
            bloque("Ingresos por servicio (registrados ese día):", self.ingresos_por_servicio, True),
            bloque("Entregas por repartidor (ese día):", self.entregas_por_repartidor),
        ]) + "\n"


class GeneradorReporte:
    """Calcula el reporte de un día y lo escribe en un archivo de texto."""

    def construir(self, fecha: date, envios: list[Envio]) -> ReporteDiario:
        """Ingresos: envíos registrados ese día, sin contar cancelados.
        Estados: envíos con algún movimiento ese día. Entregas: las hechas ese día."""
        por_estado: Counter = Counter()
        por_tipo: defaultdict = defaultdict(float)
        por_servicio: defaultdict = defaultdict(float)
        entregas: Counter = Counter()
        for envio in envios:
            historial = envio.historial()
            if any(r.fecha_hora.date() == fecha for r in historial):
                por_estado[envio.estado.nombre] += 1
            if envio.fecha_registro.date() == fecha and envio.estado.nombre != "Cancelado":
                por_tipo[envio.tipo()] += envio.total()
                por_servicio[envio.servicio.nombre()] += envio.total()
            if any(r.estado == "Entregado" and r.fecha_hora.date() == fecha for r in historial):
                entregas[envio.repartidor_id or "(sin repartidor)"] += 1
        return ReporteDiario(fecha, dict(por_estado),
                             {k: round(v, 2) for k, v in por_tipo.items()},
                             {k: round(v, 2) for k, v in por_servicio.items()},
                             dict(entregas))

    def escribir(self, reporte: ReporteDiario, ruta: str) -> str:
        """Guarda el reporte y regresa la ruta del archivo."""
        try:
            carpeta = os.path.dirname(ruta)
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(reporte.texto())
        except OSError as e:
            raise ArchivoError(f"No se pudo escribir el reporte en {ruta}: {e.strerror}") from None
        return ruta
