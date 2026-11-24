"""Excepciones propias del sistema de paquetería.

Todas heredan de PaqueteriaError, así la terminal puede capturar cualquier
error del sistema con un solo ``except PaqueteriaError`` y mostrar un mensaje
claro en lugar de un traceback.
"""


class PaqueteriaError(Exception):
    """Clase base de todos los errores del sistema."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self._mensaje = mensaje

    def __str__(self) -> str:
        return self._mensaje


class DatoInvalidoError(PaqueteriaError):
    """Un dato tiene un tipo o valor incorrecto (peso negativo, código postal sin zona...)."""

    def __init__(self, campo: str, mensaje: str):
        super().__init__(f"{campo}: {mensaje}")
        self.campo = campo


class ReglaNegocioError(PaqueteriaError):
    """Base de los errores que rompen una regla del negocio."""


class EnvioNoPermitidoError(ReglaNegocioError):
    """El envío incumple una regla (refrigerado en zona nacional o con servicio estándar)."""


class TransicionInvalidaError(ReglaNegocioError):
    """Se pidió un cambio de estado que el estado actual no permite."""


class CancelacionNoPermitidaError(ReglaNegocioError):
    """Se intentó cancelar un envío que ya salió a ruta o que está en un estado final."""


class CapacidadExcedidaError(ReglaNegocioError):
    """El envío no cabe en la capacidad libre del vehículo del repartidor."""


class EnvioNoEncontradoError(PaqueteriaError):
    """No existe ningún envío con la guía indicada."""


class ArchivoError(PaqueteriaError):
    """Base de los problemas con archivos de datos o de entrada."""


class ArchivoNoEncontradoError(ArchivoError):
    """Falta un archivo que el sistema necesita."""


class ArchivoCorruptoError(ArchivoError):
    """El archivo existe, pero su contenido no se puede leer o está incompleto."""
