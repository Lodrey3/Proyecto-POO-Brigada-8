"""Tarifas y zonas, cargadas desde archivos CSV para cambiarlas sin tocar el código."""

from __future__ import annotations

import csv

from paqueteria.excepciones.errores import (
    ArchivoCorruptoError,
    ArchivoNoEncontradoError,
    DatoInvalidoError,
)
from paqueteria.modelo.valores import Zona


def _abrir_csv(ruta: str, columnas: set[str]) -> list[tuple[int, dict]]:
    """Lee un CSV y regresa (número de renglón, datos). Revisa que estén las columnas."""
    try:
        with open(ruta, newline="", encoding="utf-8-sig") as archivo:
            lector = csv.DictReader(archivo)
            faltan = columnas - set(lector.fieldnames or [])
            if faltan:
                raise ArchivoCorruptoError(
                    f"{ruta}: faltan las columnas {', '.join(sorted(faltan))}")
            return [(n, fila) for n, fila in enumerate(lector, start=2)]
    except FileNotFoundError:
        raise ArchivoNoEncontradoError(f"No existe el archivo {ruta}") from None
    except (UnicodeDecodeError, csv.Error) as e:
        raise ArchivoCorruptoError(f"{ruta} no se puede leer como CSV: {e}") from None


class TablaTarifas:
    """Tarifa fija del sobre y tarifa por kilo de cada zona."""

    def __init__(self, sobre_por_zona: dict[Zona, float], kg_por_zona: dict[Zona, float]):
        self._sobre_por_zona = dict(sobre_por_zona)
        self._kg_por_zona = dict(kg_por_zona)

    @staticmethod
    def desde_csv(ruta: str) -> TablaTarifas:
        """Carga ``zona,tarifa_sobre,tarifa_kg``. Deben venir las tres zonas."""
        sobre, kg = {}, {}
        for n, fila in _abrir_csv(ruta, {"zona", "tarifa_sobre", "tarifa_kg"}):
            try:
                zona = Zona.desde_texto(fila["zona"])
            except DatoInvalidoError as e:
                raise ArchivoCorruptoError(f"{ruta}, renglón {n}: {e}") from None
            try:
                tarifa_sobre = float(fila["tarifa_sobre"])
                tarifa_kg = float(fila["tarifa_kg"])
            except (ValueError, TypeError):
                raise ArchivoCorruptoError(
                    f"{ruta}, renglón {n}: las tarifas '{fila['tarifa_sobre']}' y "
                    f"'{fila['tarifa_kg']}' deben ser números") from None
            if tarifa_sobre <= 0 or tarifa_kg <= 0:
                raise ArchivoCorruptoError(f"{ruta}, renglón {n}: las tarifas deben ser positivas")
            sobre[zona], kg[zona] = tarifa_sobre, tarifa_kg
        faltan = [z.value for z in Zona if z not in sobre]
        if faltan:
            raise ArchivoCorruptoError(f"{ruta}: faltan tarifas para {', '.join(faltan)}")
        return TablaTarifas(sobre, kg)

    def tarifa_sobre(self, zona: Zona) -> float:
        """Precio fijo de un sobre en esa zona."""
        return self._sobre_por_zona[zona]

    def tarifa_kg(self, zona: Zona) -> float:
        """Precio por kilo de un paquete en esa zona."""
        return self._kg_por_zona[zona]


class ResolvedorZona:
    """Decide la zona con los dos primeros dígitos del código postal."""

    def __init__(self, prefijos: dict[str, Zona]):
        self._prefijos = dict(prefijos)

    @staticmethod
    def desde_csv(ruta: str) -> ResolvedorZona:
        """Carga ``prefijo,zona`` (prefijo de dos dígitos)."""
        prefijos = {}
        for n, fila in _abrir_csv(ruta, {"prefijo", "zona"}):
            prefijo = (fila["prefijo"] or "").strip().zfill(2)
            if not (prefijo.isdigit() and len(prefijo) == 2):
                raise ArchivoCorruptoError(f"{ruta}, renglón {n}: prefijo '{fila['prefijo']}' inválido")
            try:
                prefijos[prefijo] = Zona.desde_texto(fila["zona"])
            except DatoInvalidoError as e:
                raise ArchivoCorruptoError(f"{ruta}, renglón {n}: {e}") from None
        if not prefijos:
            raise ArchivoCorruptoError(f"{ruta} no tiene ninguna zona")
        return ResolvedorZona(prefijos)

    def zona_para(self, codigo_postal: str) -> Zona:
        """Zona del código postal; lanza DatoInvalidoError si no hay regla."""
        cp = str(codigo_postal).strip()
        if not (cp.isdigit() and len(cp) == 5):
            raise DatoInvalidoError("destinatario_cp", f"'{cp}' debe tener 5 dígitos")
        try:
            return self._prefijos[cp[:2]]
        except KeyError:
            raise DatoInvalidoError("destinatario_cp", f"no hay zona de entrega para el CP {cp}") from None
