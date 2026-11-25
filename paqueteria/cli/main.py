"""Punto de entrada: ``python -m paqueteria [opciones] [comando]``.

Sin comando abre el menú. Con comando ejecuta una sola operación (útil para
probar cada función desde el README). Cualquier error del sistema se muestra
con un mensaje claro y el programa termina de forma ordenada.
"""

from __future__ import annotations

import argparse
import os
import sys

from paqueteria.cli import menu
from paqueteria.cli.menu import MenuConsola, leer_fecha, leer_fecha_hora
from paqueteria.excepciones.errores import PaqueteriaError
from paqueteria.modelo.tarifas import ResolvedorZona, TablaTarifas
from paqueteria.persistencia.repositorio_json import RepositorioJSON
from paqueteria.persistencia.serializador import SerializadorEnvios
from paqueteria.servicios.fabrica import FabricaEnvios
from paqueteria.servicios.sistema import ACCIONES, SistemaPaqueteria
from paqueteria.util.reloj import RelojSimulado, RelojSistema


def crear_parser() -> argparse.ArgumentParser:
    """Define las opciones globales y un subcomando por función."""
    p = argparse.ArgumentParser(
        prog="python -m paqueteria",
        description="Sistema de paquetería. Sin comando abre el menú interactivo.")
    p.add_argument("--fecha-hora", metavar="\"AAAA-MM-DD HH:MM\"",
                   help="fija la fecha y hora de las operaciones (para probar reglas de fecha)")
    p.add_argument("--datos", default="datos", help="carpeta con tarifas, zonas y repartidores")
    p.add_argument("--ejecucion", default="ejecucion",
                   help="carpeta donde se guardan los datos del programa")
    sub = p.add_subparsers(dest="comando", metavar="comando")

    def campos_envio(sp, completo):
        sp.add_argument("--tipo", required=True, help="sobre, paquete, fragil o refrigerado")
        sp.add_argument("--servicio", required=True, help="estandar o express")
        if completo:
            sp.add_argument("--remitente-nombre", required=True)
            sp.add_argument("--remitente-telefono", required=True)
            sp.add_argument("--remitente-cp", required=True)
            sp.add_argument("--destinatario-nombre", required=True)
            sp.add_argument("--destinatario-telefono", required=True)
            sp.add_argument("--destinatario-calle")
            sp.add_argument("--destinatario-ciudad")
        sp.add_argument("--destinatario-cp", required=True)
        sp.add_argument("--peso", dest="peso_kg", help="kg (paquetes)")
        sp.add_argument("--largo", dest="largo_cm", help="cm (paquetes)")
        sp.add_argument("--ancho", dest="ancho_cm", help="cm (paquetes)")
        sp.add_argument("--alto", dest="alto_cm", help="cm (paquetes)")
        sp.add_argument("--valor", dest="valor_declarado", help="valor declarado en $ (paquetes)")

    sub.add_parser("menu", help="abre el menú interactivo")
    campos_envio(sub.add_parser("cotizar", help="1. cotiza un envío sin registrarlo"), False)
    campos_envio(sub.add_parser("registrar", help="1. registra un envío con guía única"), True)
    sub.add_parser("rastrear", help="2. estado e historial de una guía").add_argument("guia")
    sp = sub.add_parser("estado", help="3. cambia el estado de un envío")
    sp.add_argument("guia", help="guía, o * para todas las que permitan la acción")
    sp.add_argument("accion", choices=ACCIONES)
    sub.add_parser("cancelar", help="3. cancela un envío").add_argument("guia")
    sub.add_parser("listar", help="lista envíos").add_argument("--estado")
    sub.add_parser("repartidores", help="muestra repartidores y su carga")
    sub.add_parser("asignar", help="4. asigna los envíos del almacén")
    sub.add_parser("importar", help="5. importa envíos desde CSV").add_argument("ruta")
    sub.add_parser("reporte", help="6. reporte de un día").add_argument(
        "--fecha", help="AAAA-MM-DD (por omisión, la fecha actual)")
    sp = sub.add_parser("simular", help="8. simula la jornada de reparto")
    sp.add_argument("--semilla", type=int, help="número para repetir la misma simulación")
    return p


def crear_sistema(args) -> tuple[SistemaPaqueteria, object]:
    """Carga tarifas, zonas y datos guardados; en la primera ejecución da de alta repartidores."""
    reloj = RelojSimulado(leer_fecha_hora(args.fecha_hora)) if args.fecha_hora else RelojSistema()
    tarifas = TablaTarifas.desde_csv(os.path.join(args.datos, "tarifas.csv"))
    resolvedor = ResolvedorZona.desde_csv(os.path.join(args.datos, "zonas.csv"))
    fabrica = FabricaEnvios(resolvedor)
    repositorio = RepositorioJSON(args.ejecucion, SerializadorEnvios(fabrica))
    sistema = SistemaPaqueteria(tarifas, resolvedor, repositorio, reloj, fabrica)
    if not sistema.repartidores():
        iniciales = RepositorioJSON(args.datos, obligatorio=True).cargar_repartidores()
        sistema.agregar_repartidores(iniciales)
    menu.RUTA_EJECUCION = args.ejecucion
    return sistema, reloj


def ejecutar_comando(args, sistema: SistemaPaqueteria, reloj) -> None:
    """Ejecuta el subcomando pedido."""
    campos = ("tipo", "servicio", "remitente_nombre", "remitente_telefono", "remitente_cp",
              "destinatario_nombre", "destinatario_telefono", "destinatario_cp",
              "destinatario_calle", "destinatario_ciudad", "peso_kg", "largo_cm", "ancho_cm",
              "alto_cm", "valor_declarado")
    datos = {c: getattr(args, c) for c in campos if getattr(args, c, None) is not None}
    c = args.comando
    if c == "cotizar":
        menu.mostrar_cotizacion(sistema.cotizar(datos))
    elif c == "registrar":
        menu.mostrar_registro(sistema.registrar_envio(datos))
    elif c == "rastrear":
        menu.mostrar_rastreo(sistema, args.guia)
    elif c == "estado":
        menu.cambiar_estado(sistema, args.guia, args.accion)
    elif c == "cancelar":
        sistema.cancelar_envio(args.guia)
        print(f"{args.guia.upper()} cancelado.")
    elif c == "listar":
        menu.mostrar_envios(sistema.listar_envios(args.estado))
    elif c == "repartidores":
        menu.mostrar_repartidores(sistema)
    elif c == "asignar":
        menu.mostrar_asignacion(sistema.asignar_envios())
    elif c == "importar":
        menu.mostrar_importacion(sistema.importar_csv(args.ruta))
    elif c == "reporte":
        fecha = leer_fecha(args.fecha) if args.fecha else reloj.ahora().date()
        print(sistema.generar_reporte(fecha, menu.ruta_reporte(fecha)))
        print(f"Guardado en {menu.ruta_reporte(fecha)}")
    elif c == "simular":
        ruta = menu.ruta_bitacora(reloj)
        print("Jornada en curso (la central muestra el avance):")
        print(sistema.simular_jornada(ruta, semilla=args.semilla))
        print(f"Bitácora guardada en {ruta}")


def main(argv: list[str] | None = None) -> int:
    """Arranca el programa y regresa el código de salida (0 = bien, 1 = error)."""
    args = crear_parser().parse_args(argv)
    try:
        sistema, reloj = crear_sistema(args)
        if args.comando in (None, "menu"):
            MenuConsola(sistema, reloj).ejecutar()
        else:
            ejecutar_comando(args, sistema, reloj)
        return 0
    except PaqueteriaError as e:
        print(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nOperación interrumpida.")
        return 1
    except Exception as e:  # última red de seguridad: nunca mostrar traceback
        print(f"Error inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
