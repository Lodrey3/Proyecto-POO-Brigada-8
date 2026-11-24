"""Datos de contacto del remitente y del destinatario."""

from __future__ import annotations

from dataclasses import dataclass

from paqueteria.excepciones.errores import DatoInvalidoError


@dataclass(frozen=True)
class Direccion:
    """Dirección postal opcional (calle y ciudad)."""

    calle: str
    ciudad: str


class Contacto:
    """Persona que envía o recibe. El código postal es obligatorio; la dirección, opcional."""

    def __init__(self, nombre: str, telefono: str, codigo_postal: str,
                 direccion: Direccion | None = None):
        self._nombre = str(nombre).strip()
        self._telefono = str(telefono).strip()
        self._codigo_postal = str(codigo_postal).strip()
        self._direccion = direccion

    @property
    def nombre(self) -> str:
        """Nombre de la persona."""
        return self._nombre

    @property
    def telefono(self) -> str:
        """Teléfono a 10 dígitos."""
        return self._telefono

    @property
    def codigo_postal(self) -> str:
        """Código postal a 5 dígitos."""
        return self._codigo_postal

    @property
    def direccion(self) -> Direccion | None:
        """Dirección postal, si se capturó."""
        return self._direccion

    def validar(self, rol: str) -> None:
        """Revisa nombre, teléfono y código postal; ``rol`` se usa en el mensaje de error."""
        if not self._nombre:
            raise DatoInvalidoError(f"{rol}_nombre", "no puede estar vacío")
        if not (self._telefono.isdigit() and len(self._telefono) == 10):
            raise DatoInvalidoError(f"{rol}_telefono", f"'{self._telefono}' debe tener 10 dígitos")
        if not (self._codigo_postal.isdigit() and len(self._codigo_postal) == 5):
            raise DatoInvalidoError(f"{rol}_cp", f"'{self._codigo_postal}' debe tener 5 dígitos")

    def __str__(self) -> str:
        return f"{self._nombre} (CP {self._codigo_postal})"
