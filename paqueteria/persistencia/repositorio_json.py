"""Repositorio en archivos JSON con escritura atómica."""

from __future__ import annotations

import json
import os
import tempfile
import threading

from paqueteria.excepciones.errores import ArchivoCorruptoError, ArchivoError, ArchivoNoEncontradoError
from paqueteria.modelo.envio import Envio
from paqueteria.modelo.repartidor import Repartidor
from paqueteria.modelo.vehiculo import Camioneta, Motocicleta, Vehiculo
from paqueteria.persistencia.repositorio import Repositorio
from paqueteria.persistencia.serializador import SerializadorEnvios

_VEHICULOS: dict[str, type[Vehiculo]] = {"motocicleta": Motocicleta, "camioneta": Camioneta}


class RepositorioJSON(Repositorio):
    """Guarda envios.json, repartidores.json y contador.json en un directorio.

    Si ``obligatorio`` es False, un archivo que falta se toma como «primera
    ejecución» y se regresa vacío; si es True, se lanza ArchivoNoEncontradoError.
    Un archivo dañado siempre lanza ArchivoCorruptoError y nunca se sobrescribe solo.
    """

    def __init__(self, directorio: str, serializador: SerializadorEnvios | None = None,
                 obligatorio: bool = False):
        self._directorio = directorio
        self._serializador = serializador
        self._obligatorio = obligatorio
        self._lock = threading.Lock()

    def _ruta(self, nombre: str) -> str:
        return os.path.join(self._directorio, nombre)

    def cargar_envios(self) -> list[Envio]:
        datos = self._leer(self._ruta("envios.json"), [])
        if not isinstance(datos, list):
            raise ArchivoCorruptoError(f"{self._ruta('envios.json')} debe contener una lista")
        return [self._serializador.desde_dict(d) for d in datos]

    def guardar_envios(self, envios: list[Envio]) -> None:
        self._escribir_atomico(self._ruta("envios.json"),
                               [self._serializador.a_dict(e) for e in envios])

    def cargar_repartidores(self) -> list[Repartidor]:
        ruta = self._ruta("repartidores.json")
        datos = self._leer(ruta, [])
        repartidores, ids = [], set()
        try:
            for d in datos:
                vehiculo = _VEHICULOS[str(d["vehiculo"]).lower()]()
                rid = str(d["id"]).strip()
                if not rid or rid in ids:
                    raise ValueError(f"id repetido o vacío: '{rid}'")
                ids.add(rid)
                repartidores.append(Repartidor(rid, str(d["nombre"]), vehiculo))
        except KeyError as e:
            raise ArchivoCorruptoError(f"{ruta}: falta el dato {e} o el vehículo no existe") from None
        except (TypeError, ValueError) as e:
            raise ArchivoCorruptoError(f"{ruta}: repartidor inválido ({e})") from None
        return repartidores

    def guardar_repartidores(self, reps: list[Repartidor]) -> None:
        self._escribir_atomico(self._ruta("repartidores.json"),
                               [{"id": r.id, "nombre": r.nombre, "vehiculo": r.vehiculo.tipo()}
                                for r in reps])

    def cargar_contador(self) -> int:
        ruta = self._ruta("contador.json")
        datos = self._leer(ruta, {"ultimo": 0})
        try:
            valor = int(datos["ultimo"])
        except (KeyError, TypeError, ValueError):
            raise ArchivoCorruptoError(f"{ruta}: no tiene un número 'ultimo' válido") from None
        if valor < 0:
            raise ArchivoCorruptoError(f"{ruta}: el contador no puede ser negativo")
        return valor

    def guardar_contador(self, valor: int) -> None:
        self._escribir_atomico(self._ruta("contador.json"), {"ultimo": valor})

    def _escribir_atomico(self, ruta: str, datos) -> None:
        """Escribe en un temporal y lo renombra: un corte a medias no daña el archivo."""
        with self._lock:
            try:
                os.makedirs(self._directorio, exist_ok=True)
                fd, temporal = tempfile.mkstemp(dir=self._directorio, suffix=".tmp")
                with os.fdopen(fd, "w", encoding="utf-8") as archivo:
                    json.dump(datos, archivo, ensure_ascii=False, indent=2)
                os.replace(temporal, ruta)
            except OSError as e:
                raise ArchivoError(f"No se pudo guardar {ruta}: {e.strerror}") from None

    def _leer(self, ruta: str, vacio):
        """Lee un JSON; maneja archivo faltante y archivo dañado."""
        with self._lock:
            try:
                with open(ruta, encoding="utf-8") as archivo:
                    return json.load(archivo)
            except FileNotFoundError:
                if self._obligatorio:
                    raise ArchivoNoEncontradoError(f"No existe el archivo {ruta}") from None
                return vacio
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ArchivoCorruptoError(
                    f"El archivo {ruta} está dañado ({e}). Corrígelo o bórralo para empezar de cero."
                ) from None
            except OSError as e:
                raise ArchivoError(f"No se pudo leer {ruta}: {e.strerror}") from None
