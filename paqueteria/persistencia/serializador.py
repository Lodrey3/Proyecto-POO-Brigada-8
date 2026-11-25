"""Conversión de envíos a diccionarios (para JSON) y de regreso."""

from __future__ import annotations

from datetime import datetime

from paqueteria.excepciones.errores import ArchivoCorruptoError, PaqueteriaError
from paqueteria.modelo.envio import Envio, Paquete
from paqueteria.modelo.estados import EstadoEnvio
from paqueteria.modelo.valores import Cotizacion, RegistroEstado
from paqueteria.servicios.fabrica import FabricaEnvios

FORMATO = "%Y-%m-%d %H:%M"


class SerializadorEnvios:
    """Convierte un envío en diccionario y lo reconstruye con la fábrica."""

    def __init__(self, fabrica: FabricaEnvios):
        self._fabrica = fabrica

    def a_dict(self, envio: Envio) -> dict:
        """Diccionario con todos los datos del envío, incluido su historial."""
        d, r = envio.destinatario, envio.remitente
        datos = {
            "guia": envio.guia,
            "tipo": envio.tipo(),
            "servicio": envio.servicio.nombre(),
            "remitente_nombre": r.nombre, "remitente_telefono": r.telefono,
            "remitente_cp": r.codigo_postal,
            "destinatario_nombre": d.nombre, "destinatario_telefono": d.telefono,
            "destinatario_cp": d.codigo_postal,
            "destinatario_calle": d.direccion.calle if d.direccion else "",
            "destinatario_ciudad": d.direccion.ciudad if d.direccion else "",
            "fecha_registro": envio.fecha_registro.strftime(FORMATO),
            "estado": envio.estado.nombre,
            "intentos_fallidos": envio.intentos_fallidos,
            "repartidor_id": envio.repartidor_id,
            "cotizacion": vars(envio.cotizacion) if envio.cotizacion else None,
            "historial": [{"estado": h.estado, "fecha_hora": h.fecha_hora.strftime(FORMATO),
                           "nota": h.nota} for h in envio.historial()],
        }
        if isinstance(envio, Paquete):
            datos.update(peso_kg=envio.peso_kg, largo_cm=envio.dimensiones.largo_cm,
                         ancho_cm=envio.dimensiones.ancho_cm, alto_cm=envio.dimensiones.alto_cm,
                         valor_declarado=envio.valor_declarado)
        return datos

    def desde_dict(self, datos: dict) -> Envio:
        """Reconstruye el envío; lanza ArchivoCorruptoError si los datos no cuadran."""
        guia = datos.get("guia", "?") if isinstance(datos, dict) else "?"
        try:
            entrada = dict(datos)
            entrada["fecha_registro"] = datetime.strptime(datos["fecha_registro"], FORMATO)
            envio = self._fabrica.crear(entrada)
            historial = [RegistroEstado(h["estado"], datetime.strptime(h["fecha_hora"], FORMATO),
                                        h.get("nota", "")) for h in datos["historial"]]
            cotizacion = Cotizacion(**datos["cotizacion"]) if datos.get("cotizacion") else None
            envio.restaurar(datos["guia"], EstadoEnvio.desde_nombre(datos["estado"]), historial,
                            int(datos.get("intentos_fallidos", 0)), datos.get("repartidor_id"),
                            cotizacion)
            return envio
        except PaqueteriaError as e:
            raise ArchivoCorruptoError(f"El envío {guia} guardado no es válido: {e}") from None
        except (KeyError, TypeError, ValueError) as e:
            raise ArchivoCorruptoError(f"El envío {guia} guardado está incompleto ({e})") from None
