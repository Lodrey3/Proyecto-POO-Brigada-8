"""Importación de envíos de un cliente empresarial desde CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime

from paqueteria.excepciones.errores import (
    ArchivoCorruptoError,
    ArchivoNoEncontradoError,
    PaqueteriaError,
)
from paqueteria.modelo.envio import Envio
from paqueteria.servicios.fabrica import FabricaEnvios

COLUMNAS = {"tipo", "servicio", "remitente_nombre", "remitente_telefono", "remitente_cp",
            "destinatario_nombre", "destinatario_telefono", "destinatario_cp"}


@dataclass(frozen=True)
class RenglonRechazado:
    """Un renglón que no se pudo importar: número, contenido y motivo."""

    numero: int
    contenido: str
    motivo: str


@dataclass(frozen=True)
class ResultadoImportacion:
    """Envíos válidos y renglones rechazados de un archivo."""

    aceptados: list[Envio] = field(default_factory=list)
    rechazados: list[RenglonRechazado] = field(default_factory=list)


class ImportadorEnvios:
    """Lee el CSV renglón por renglón; un renglón malo no detiene la importación."""

    def __init__(self, fabrica: FabricaEnvios):
        self._fabrica = fabrica

    def importar(self, ruta: str, fecha: datetime | None = None) -> ResultadoImportacion:
        """Crea un envío por renglón válido y anota el motivo de cada rechazo."""
        try:
            with open(ruta, newline="", encoding="utf-8-sig") as archivo:
                lector = csv.DictReader(archivo)
                faltan = COLUMNAS - set(lector.fieldnames or [])
                if faltan:
                    raise ArchivoCorruptoError(
                        f"{ruta}: faltan las columnas {', '.join(sorted(faltan))}")
                aceptados, rechazados = [], []
                for numero, fila in enumerate(lector, start=2):
                    contenido = ",".join(str(v) for v in fila.values() if v is not None)
                    if None in fila:
                        rechazados.append(RenglonRechazado(numero, contenido,
                                                           "tiene más columnas que el encabezado"))
                        continue
                    datos = dict(fila, fecha_registro=fecha)
                    try:
                        aceptados.append(self._fabrica.crear(datos))
                    except PaqueteriaError as e:
                        rechazados.append(RenglonRechazado(numero, contenido, str(e)))
        except FileNotFoundError:
            raise ArchivoNoEncontradoError(f"No existe el archivo {ruta}") from None
        except IsADirectoryError:
            raise ArchivoNoEncontradoError(f"{ruta} es una carpeta, no un archivo") from None
        except (UnicodeDecodeError, csv.Error) as e:
            raise ArchivoCorruptoError(f"{ruta} no se puede leer como CSV: {e}") from None
        return ResultadoImportacion(aceptados, rechazados)
