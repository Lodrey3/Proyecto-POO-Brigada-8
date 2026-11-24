"""Objetos de valor del modelo: datos inmutables que no cambian por accidente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from paqueteria.excepciones.errores import DatoInvalidoError


class Zona(Enum):
    """Zona de destino de un envío; decide la tarifa."""

    LOCAL = "local"
    REGIONAL = "regional"
    NACIONAL = "nacional"

    @staticmethod
    def desde_texto(texto: str) -> "Zona":
        """Convierte 'local', 'regional' o 'nacional' en una Zona."""
        try:
            return Zona(str(texto).strip().lower())
        except ValueError:
            raise DatoInvalidoError("zona", f"'{texto}' no es local, regional ni nacional") from None

    def __str__(self) -> str:
        return self.value.capitalize()


@dataclass(frozen=True)
class Dimensiones:
    """Medidas de un paquete en centímetros."""

    largo_cm: float
    ancho_cm: float
    alto_cm: float

    def peso_volumetrico_kg(self) -> float:
        """Peso volumétrico: largo × ancho × alto / 5000."""
        return self.largo_cm * self.ancho_cm * self.alto_cm / 5000


@dataclass(frozen=True)
class RegistroEstado:
    """Una entrada del historial: a qué estado pasó el envío, cuándo y por qué."""

    estado: str
    fecha_hora: datetime
    nota: str = ""

    def __str__(self) -> str:
        texto = f"{self.fecha_hora:%Y-%m-%d %H:%M}  {self.estado}"
        return f"{texto}  ({self.nota})" if self.nota else texto


@dataclass(frozen=True)
class Cotizacion:
    """Desglose del precio de un envío y sus días de entrega."""

    base: float
    recargo_fragil: float
    recargo_servicio: float
    seguro: float
    total: float
    dias_min: int
    dias_max: int

    def __str__(self) -> str:
        lineas = [f"  Base:              ${self.base:,.2f}"]
        if self.recargo_fragil:
            lineas.append(f"  Recargo frágil:    ${self.recargo_fragil:,.2f}")
        if self.recargo_servicio:
            lineas.append(f"  Recargo express:   ${self.recargo_servicio:,.2f}")
        if self.seguro:
            lineas.append(f"  Seguro (3 %):      ${self.seguro:,.2f}")
        lineas.append(f"  TOTAL:             ${self.total:,.2f}")
        if self.dias_min == self.dias_max:
            lineas.append(f"  Entrega en {self.dias_min} día(s)")
        else:
            lineas.append(f"  Entrega en {self.dias_min} a {self.dias_max} días")
        return "\n".join(lineas)
