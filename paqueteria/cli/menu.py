"""Menú de texto y funciones para mostrar resultados en la terminal."""

from __future__ import annotations

from datetime import date, datetime

from paqueteria.excepciones.errores import DatoInvalidoError, PaqueteriaError
from paqueteria.servicios.sistema import ACCIONES, SistemaPaqueteria
from paqueteria.util.reloj import Reloj, RelojSimulado

RUTA_EJECUCION = "ejecucion"


def leer_fecha_hora(texto: str) -> datetime:
    """Convierte 'AAAA-MM-DD HH:MM' en datetime."""
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        raise DatoInvalidoError("fecha-hora", f"'{texto}' no tiene el formato AAAA-MM-DD HH:MM") from None


def leer_fecha(texto: str) -> date:
    """Convierte 'AAAA-MM-DD' en date."""
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise DatoInvalidoError("fecha", f"'{texto}' no tiene el formato AAAA-MM-DD") from None


# ----- funciones para mostrar (las usan el menú y los comandos) ------------
def mostrar_cotizacion(cotizacion) -> None:
    print("Cotización:")
    print(cotizacion)


def mostrar_registro(envio) -> None:
    print(f"Envío registrado con la guía {envio.guia}")
    print(envio.cotizacion)


def mostrar_rastreo(sistema: SistemaPaqueteria, guia: str) -> None:
    envio = sistema.obtener_envio(guia)
    estado, historial = sistema.rastrear(guia)
    print(f"Guía {envio.guia}: {envio.tipo()}, servicio {envio.servicio.nombre()}, "
          f"zona {envio.zona}, para {envio.destinatario}")
    print(f"Estado actual: {estado}   Intentos fallidos: {envio.intentos_fallidos}"
          + (f"   Repartidor: {envio.repartidor_id}" if envio.repartidor_id else ""))
    print("Historial:")
    for registro in historial:
        print(f"  {registro}")


def cambiar_estado(sistema: SistemaPaqueteria, guia: str, accion: str) -> None:
    """Aplica la acción a una guía, o a todas las que la permitan si la guía es '*'."""
    if guia.strip() != "*":
        sistema.cambiar_estado(guia, accion)
        estado, _ = sistema.rastrear(guia)
        print(f"{guia.upper()}: ahora está en {estado}")
        return
    hechos = 0
    for envio in sistema.listar_envios():
        try:
            sistema.cambiar_estado(envio.guia, accion)
            hechos += 1
        except PaqueteriaError:
            pass
    print(f"Se aplicó '{accion}' a {hechos} envío(s).")


def mostrar_envios(envios) -> None:
    if not envios:
        print("No hay envíos.")
    for envio in envios:
        print(f"  {envio}")


def mostrar_repartidores(sistema: SistemaPaqueteria) -> None:
    for rep in sistema.repartidores():
        print(f"  {rep}")


def mostrar_asignacion(resultado) -> None:
    if not resultado.asignados and not resultado.sin_asignar:
        print("No hay envíos en el almacén pendientes de asignar.")
    for rid, guias in resultado.asignados.items():
        print(f"  {rid} recibe {len(guias)}: {', '.join(guias)}")
    if resultado.sin_asignar:
        print(f"  No cupieron (siguen en almacén): {', '.join(resultado.sin_asignar)}")


def mostrar_importacion(resultado) -> None:
    print(f"Importados: {len(resultado.aceptados)}   Rechazados: {len(resultado.rechazados)}")
    for envio in resultado.aceptados:
        print(f"  OK  {envio.guia}  {envio.tipo()} -> {envio.destinatario}  ${envio.total():,.2f}")
    for renglon in resultado.rechazados:
        print(f"  RECHAZADO renglón {renglon.numero}: {renglon.motivo}")
        print(f"      [{renglon.contenido}]")


def ruta_reporte(fecha: date) -> str:
    return f"{RUTA_EJECUCION}/reportes/reporte_{fecha:%Y-%m-%d}.txt"


def ruta_bitacora(reloj: Reloj) -> str:
    return f"{RUTA_EJECUCION}/bitacoras/jornada_{reloj.ahora():%Y-%m-%d_%H%M}.txt"


# ----- menú interactivo ----------------------------------------------------
class MenuConsola:
    """Menú de texto. Atrapa los errores del sistema para que nunca salga un traceback."""

    OPCIONES = [
        ("1", "Cotizar un envío"),
        ("2", "Registrar un envío"),
        ("3", "Rastrear una guía"),
        ("4", "Cambiar el estado de un envío (o cancelarlo)"),
        ("5", "Listar envíos"),
        ("6", "Ver repartidores y asignar envíos del almacén"),
        ("7", "Importar envíos desde CSV"),
        ("8", "Generar el reporte de un día"),
        ("9", "Simular la jornada de reparto"),
        ("f", "Fijar la fecha y hora (solo si se inició con --fecha-hora)"),
        ("0", "Salir"),
    ]

    def __init__(self, sistema: SistemaPaqueteria, reloj: Reloj):
        self._sistema = sistema
        self._reloj = reloj
        self._acciones = {
            "1": self._cotizar, "2": self._registrar, "3": self._rastrear,
            "4": self._cambiar_estado, "5": self._listar, "6": self._asignar,
            "7": self._importar, "8": self._reporte, "9": self._simular, "f": self._fijar_fecha,
        }

    def ejecutar(self) -> None:
        """Muestra el menú hasta que el usuario elige salir."""
        while True:
            print(f"\n=== Paquetería  ({self._reloj.ahora():%Y-%m-%d %H:%M}) ===")
            for clave, texto in self.OPCIONES:
                print(f"  {clave}) {texto}")
            try:
                opcion = input("Opción: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nHasta luego.")
                return
            if opcion == "0":
                print("Hasta luego.")
                return
            accion = self._acciones.get(opcion)
            if accion is None:
                print("Opción no válida.")
                continue
            try:
                accion()
            except PaqueteriaError as e:
                print(f"Error: {e}")
            except (EOFError, KeyboardInterrupt):
                print("\nOperación cancelada.")
            except Exception as e:  # última red de seguridad: nunca mostrar traceback
                print(f"Error inesperado: {e}")

    # ----- captura de datos --------------------------------------------------
    @staticmethod
    def _pedir(texto: str, obligatorio: bool = True) -> str:
        while True:
            valor = input(f"  {texto}: ").strip()
            if valor or not obligatorio:
                return valor
            print("  Este dato es obligatorio.")

    def _datos_envio(self, completo: bool) -> dict:
        datos = {
            "tipo": self._pedir("Tipo (sobre, paquete, fragil, refrigerado)"),
            "servicio": self._pedir("Servicio (estandar, express)"),
        }
        if completo:
            datos["remitente_nombre"] = self._pedir("Remitente - nombre")
            datos["remitente_telefono"] = self._pedir("Remitente - teléfono (10 dígitos)")
            datos["remitente_cp"] = self._pedir("Remitente - código postal")
            datos["destinatario_nombre"] = self._pedir("Destinatario - nombre")
            datos["destinatario_telefono"] = self._pedir("Destinatario - teléfono (10 dígitos)")
        datos["destinatario_cp"] = self._pedir("Destinatario - código postal")
        if completo:
            datos["destinatario_calle"] = self._pedir("Destinatario - calle (opcional)", False)
            datos["destinatario_ciudad"] = self._pedir("Destinatario - ciudad (opcional)", False)
        if datos["tipo"].strip().lower() != "sobre":
            datos["peso_kg"] = self._pedir("Peso en kg")
            datos["largo_cm"] = self._pedir("Largo en cm")
            datos["ancho_cm"] = self._pedir("Ancho en cm")
            datos["alto_cm"] = self._pedir("Alto en cm")
            datos["valor_declarado"] = self._pedir("Valor declarado en $")
        return datos

    # ----- opciones ----------------------------------------------------------
    def _cotizar(self):
        mostrar_cotizacion(self._sistema.cotizar(self._datos_envio(completo=False)))

    def _registrar(self):
        mostrar_registro(self._sistema.registrar_envio(self._datos_envio(completo=True)))

    def _rastrear(self):
        mostrar_rastreo(self._sistema, self._pedir("Guía"))

    def _cambiar_estado(self):
        guia = self._pedir("Guía (o * para todas las que lo permitan)")
        for i, accion in enumerate(ACCIONES, start=1):
            print(f"    {i}) {accion}")
        eleccion = self._pedir("Acción")
        if not (eleccion.isdigit() and 1 <= int(eleccion) <= len(ACCIONES)):
            raise DatoInvalidoError("acción", f"elige un número del 1 al {len(ACCIONES)}")
        cambiar_estado(self._sistema, guia, ACCIONES[int(eleccion) - 1])

    def _listar(self):
        estado = self._pedir("Estado (vacío = todos; Registrado, EnAlmacen, EnRuta, "
                             "Entregado, Devuelto, Cancelado)", False)
        mostrar_envios(self._sistema.listar_envios(estado or None))

    def _asignar(self):
        print("Repartidores:")
        mostrar_repartidores(self._sistema)
        if self._pedir("¿Asignar los envíos del almacén? (s/n)").lower().startswith("s"):
            mostrar_asignacion(self._sistema.asignar_envios())
            mostrar_repartidores(self._sistema)

    def _importar(self):
        mostrar_importacion(self._sistema.importar_csv(self._pedir("Ruta del CSV")))

    def _reporte(self):
        texto = self._pedir("Fecha AAAA-MM-DD (vacío = hoy)", False)
        fecha = leer_fecha(texto) if texto else self._reloj.ahora().date()
        print(self._sistema.generar_reporte(fecha, ruta_reporte(fecha)))
        print(f"Guardado en {ruta_reporte(fecha)}")

    def _simular(self):
        ruta = ruta_bitacora(self._reloj)
        print("Jornada en curso (la central muestra el avance):")
        print(self._sistema.simular_jornada(ruta))
        print(f"Bitácora guardada en {ruta}")

    def _fijar_fecha(self):
        if not isinstance(self._reloj, RelojSimulado):
            print("El reloj es el de la computadora. Inicia con --fecha-hora \"AAAA-MM-DD HH:MM\" "
                  "para poder fijarlo.")
            return
        self._reloj.fijar(leer_fecha_hora(self._pedir("Nueva fecha y hora AAAA-MM-DD HH:MM")))
        print(f"Fecha fijada: {self._reloj.ahora():%Y-%m-%d %H:%M}")
