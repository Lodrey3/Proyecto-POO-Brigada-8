"""Fábrica de envíos (patrón Factory).

Es el único lugar donde se crean envíos, tanto desde el menú como desde el CSV
o al cargar los archivos, así todos pasan por las mismas validaciones.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime

from paqueteria.excepciones.errores import DatoInvalidoError
from paqueteria.modelo.contacto import Contacto, Direccion
from paqueteria.modelo.envio import Envio, Paquete, PaqueteFragil, PaqueteRefrigerado, Sobre
from paqueteria.modelo.servicio import Servicio, ServicioEstandar, ServicioExpress
from paqueteria.modelo.tarifas import ResolvedorZona
from paqueteria.modelo.valores import Dimensiones


def _normalizar(texto) -> str:
    """Minúsculas, sin acentos y sin espacios sobrantes: 'Paquete Frágil' -> 'paquete fragil'."""
    texto = unicodedata.normalize("NFD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().replace("_", " ").split())


class FabricaEnvios:
    """Crea el tipo de envío correcto a partir de un diccionario de datos."""

    def __init__(self, resolvedor: ResolvedorZona):
        self._resolvedor = resolvedor
        self._registro_tipos: dict[str, type[Envio]] = {
            "sobre": Sobre,
            "paquete": Paquete,
            "fragil": PaqueteFragil,
            "paquete fragil": PaqueteFragil,
            "refrigerado": PaqueteRefrigerado,
            "paquete refrigerado": PaqueteRefrigerado,
        }
        self._servicios: dict[str, type[Servicio]] = {
            "estandar": ServicioEstandar,
            "express": ServicioExpress,
        }

    def tipos(self) -> list[str]:
        """Claves cortas de los tipos que se pueden crear."""
        return ["sobre", "paquete", "fragil", "refrigerado"]

    def crear(self, datos: dict) -> Envio:
        """Crea y valida un envío. Lanza DatoInvalidoError o EnvioNoPermitidoError.

        Claves de ``datos``: tipo, servicio, remitente_nombre, remitente_telefono,
        remitente_cp, destinatario_nombre, destinatario_telefono, destinatario_cp,
        destinatario_calle y destinatario_ciudad (opcionales), fecha_registro y,
        para paquetes, peso_kg, largo_cm, ancho_cm, alto_cm, valor_declarado.
        """
        clase = self._registro_tipos.get(_normalizar(datos.get("tipo")))
        if clase is None:
            raise DatoInvalidoError(
                "tipo", f"'{datos.get('tipo')}' no es válido; usa {', '.join(self.tipos())}")
        servicio_cls = self._servicios.get(_normalizar(datos.get("servicio")))
        if servicio_cls is None:
            raise DatoInvalidoError(
                "servicio", f"'{datos.get('servicio')}' no es válido; usa estandar o express")

        remitente = Contacto(self._texto(datos, "remitente_nombre"),
                             self._texto(datos, "remitente_telefono"),
                             self._texto(datos, "remitente_cp"))
        calle = str(datos.get("destinatario_calle") or "").strip()
        ciudad = str(datos.get("destinatario_ciudad") or "").strip()
        direccion = Direccion(calle, ciudad) if (calle or ciudad) else None
        destinatario = Contacto(self._texto(datos, "destinatario_nombre"),
                                self._texto(datos, "destinatario_telefono"),
                                self._texto(datos, "destinatario_cp"), direccion)
        zona = self._resolvedor.zona_para(destinatario.codigo_postal)
        fecha = datos.get("fecha_registro")
        if not isinstance(fecha, datetime):
            raise DatoInvalidoError("fecha_registro", "falta la fecha de registro")

        if issubclass(clase, Paquete):
            dimensiones = Dimensiones(self._numero(datos, "largo_cm"),
                                      self._numero(datos, "ancho_cm"),
                                      self._numero(datos, "alto_cm"))
            envio = clase(remitente, destinatario, zona, servicio_cls(), fecha,
                          self._numero(datos, "peso_kg"), dimensiones,
                          self._numero(datos, "valor_declarado"))
        else:
            envio = clase(remitente, destinatario, zona, servicio_cls(), fecha)
        envio.validar()
        return envio

    @staticmethod
    def _texto(datos: dict, campo: str) -> str:
        valor = str(datos.get(campo) or "").strip()
        if not valor:
            raise DatoInvalidoError(campo, "es obligatorio")
        return valor

    @staticmethod
    def _numero(datos: dict, campo: str) -> float:
        valor = datos.get(campo)
        if valor is None or str(valor).strip() == "":
            raise DatoInvalidoError(campo, "es obligatorio para paquetes")
        try:
            return float(str(valor).strip().replace(",", "."))
        except ValueError:
            raise DatoInvalidoError(campo, f"'{valor}' no es un número") from None
