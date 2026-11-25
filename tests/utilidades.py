"""Objetos de prueba compartidos por las pruebas."""

from datetime import datetime

from paqueteria.modelo.tarifas import ResolvedorZona, TablaTarifas
from paqueteria.modelo.valores import Zona
from paqueteria.servicios.fabrica import FabricaEnvios

FECHA = datetime(2026, 11, 20, 9, 0)
TARIFAS = TablaTarifas({Zona.LOCAL: 60, Zona.REGIONAL: 90, Zona.NACIONAL: 150},
                       {Zona.LOCAL: 25, Zona.REGIONAL: 40, Zona.NACIONAL: 65})
RESOLVEDOR = ResolvedorZona({"03": Zona.LOCAL, "53": Zona.REGIONAL, "44": Zona.NACIONAL})
FABRICA = FabricaEnvios(RESOLVEDOR)


def datos(**cambios) -> dict:
    """Datos válidos de un paquete local estándar; se pueden cambiar campos."""
    base = {
        "tipo": "paquete", "servicio": "estandar",
        "remitente_nombre": "Héctor", "remitente_telefono": "5512345678", "remitente_cp": "03100",
        "destinatario_nombre": "Ana", "destinatario_telefono": "5587654321",
        "destinatario_cp": "03100", "peso_kg": "3", "largo_cm": "30", "ancho_cm": "20",
        "alto_cm": "15", "valor_declarado": "500", "fecha_registro": FECHA,
    }
    base.update(cambios)
    return base


def envio_registrado(guia="PQ-20261120-0001", **cambios):
    """Envío creado, cotizado y con guía."""
    envio = FABRICA.crear(datos(**cambios))
    envio.cotizar(TARIFAS)
    envio.asignar_guia(guia)
    return envio
