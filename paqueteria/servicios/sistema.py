"""Fachada del sistema: la terminal solo habla con SistemaPaqueteria."""

from __future__ import annotations

from datetime import date

from paqueteria.concurrencia.central import CentralMonitoreo
from paqueteria.concurrencia.observadores import BitacoraArchivo, VistaConsola
from paqueteria.concurrencia.simulador import ResumenJornada, SimuladorJornada
from paqueteria.excepciones.errores import DatoInvalidoError, PaqueteriaError
from paqueteria.modelo.envio import Envio
from paqueteria.modelo.repartidor import Repartidor
from paqueteria.modelo.tarifas import ResolvedorZona, TablaTarifas
from paqueteria.modelo.valores import Cotizacion, RegistroEstado
from paqueteria.persistencia.repositorio import Repositorio
from paqueteria.servicios.asignador import AsignadorEnvios, ResultadoAsignacion
from paqueteria.servicios.fabrica import FabricaEnvios
from paqueteria.servicios.guias import GeneradorGuias
from paqueteria.servicios.importador import ImportadorEnvios, ResultadoImportacion
from paqueteria.servicios.registro import RegistroEnvios
from paqueteria.servicios.reportes import GeneradorReporte
from paqueteria.util.reloj import Reloj

ACCIONES = ("ingresar_a_almacen", "salir_a_ruta", "entregar", "registrar_intento_fallido",
            "cancelar")

# Para cotizar no se necesitan los contactos reales; se usan estos de relleno.
_CONTACTOS_COTIZACION = {
    "remitente_nombre": "Cotización", "remitente_telefono": "0000000000",
    "destinatario_nombre": "Cotización", "destinatario_telefono": "0000000000",
}


class SistemaPaqueteria:
    """Ofrece una operación por función mínima y delega el trabajo en las demás clases."""

    def __init__(self, tarifas: TablaTarifas, resolvedor: ResolvedorZona,
                 repositorio: Repositorio, reloj: Reloj, fabrica: FabricaEnvios | None = None):
        self._tarifas = tarifas
        self._resolvedor = resolvedor
        self._fabrica = fabrica or FabricaEnvios(resolvedor)
        self._registro = RegistroEnvios()
        self._repositorio = repositorio
        self._reloj = reloj
        self._guias = GeneradorGuias(repositorio.cargar_contador())
        for envio in repositorio.cargar_envios():
            self._registro.agregar(envio)
        self._repartidores: list[Repartidor] = repositorio.cargar_repartidores()
        self._reasignar_pendientes()

    def _reasignar_pendientes(self) -> None:
        """Al cargar, vuelve a poner en cada repartidor los envíos que tenía asignados."""
        por_id = {r.id: r for r in self._repartidores}
        for envio in self._registro.todos():
            rep = por_id.get(envio.repartidor_id)
            if rep and envio.estado.nombre == "EnAlmacen":
                rep.asignar(envio)

    def agregar_repartidores(self, repartidores: list[Repartidor]) -> None:
        """Da de alta repartidores (se usa en la primera ejecución con los de ejemplo)."""
        ids = {r.id for r in self._repartidores}
        self._repartidores.extend(r for r in repartidores if r.id not in ids)
        self.guardar()

    # ----- 1. cotizar y registrar ------------------------------------------
    def cotizar(self, datos: dict) -> Cotizacion:
        """Calcula el precio sin registrar ni gastar guía."""
        entrada = {**_CONTACTOS_COTIZACION, **datos, "fecha_registro": self._reloj.ahora()}
        entrada.setdefault("remitente_cp", entrada.get("destinatario_cp"))
        return self._fabrica.crear(entrada).cotizar(self._tarifas)

    def registrar_envio(self, datos: dict) -> Envio:
        """Crea, valida, cotiza y registra el envío con una guía única."""
        envio = self._fabrica.crear({**datos, "fecha_registro": self._reloj.ahora()})
        self._dar_de_alta(envio)
        self.guardar()
        return envio

    def _dar_de_alta(self, envio: Envio) -> None:
        envio.cotizar(self._tarifas)
        envio.asignar_guia(self._guias.siguiente(envio.fecha_registro.date()))
        self._registro.agregar(envio)

    # ----- 2 y 3. rastrear y cambiar estado --------------------------------
    def rastrear(self, guia: str) -> tuple[str, list[RegistroEstado]]:
        """Estado actual y el historial completo de una guía."""
        envio = self._registro.obtener(guia)
        return envio.estado.nombre, list(envio.historial())

    def obtener_envio(self, guia: str) -> Envio:
        """Regresa el envío de una guía (para mostrar sus datos)."""
        return self._registro.obtener(guia)

    def cambiar_estado(self, guia: str, accion: str) -> None:
        """Aplica una acción al envío; el estado actual decide si se permite."""
        if accion not in ACCIONES:
            raise DatoInvalidoError("accion", f"'{accion}' no existe; usa {', '.join(ACCIONES)}")
        if accion == "cancelar":
            self.cancelar_envio(guia)
            return
        envio = self._registro.obtener(guia)
        if accion == "salir_a_ruta" and envio.repartidor_id:
            raise PaqueteriaError(f"{guia} ya está asignado a {envio.repartidor_id}; "
                                  "saldrá a ruta en la simulación de la jornada")
        getattr(envio, accion)(self._reloj.ahora())
        self.guardar()

    def cancelar_envio(self, guia: str) -> None:
        """Cancela el envío (solo antes de salir a ruta) y lo quita de su repartidor."""
        envio = self._registro.obtener(guia)
        envio.cancelar(self._reloj.ahora())
        for rep in self._repartidores:
            rep.retirar(envio)
        self.guardar()

    def listar_envios(self, estado: str | None = None) -> list[Envio]:
        """Todos los envíos, o solo los que están en el estado indicado."""
        envios = self._registro.todos()
        return [e for e in envios if estado is None or e.estado.nombre == estado]

    # ----- 4. asignar -----------------------------------------------------
    def repartidores(self) -> list[Repartidor]:
        """Lista de repartidores con su carga actual."""
        return list(self._repartidores)

    def asignar_envios(self) -> ResultadoAsignacion:
        """Asigna los envíos del almacén que aún no tienen repartidor."""
        resultado = AsignadorEnvios().asignar(self._registro.en_almacen(), self._repartidores)
        self.guardar()
        return resultado

    # ----- 5. importar -----------------------------------------------------
    def importar_csv(self, ruta: str) -> ResultadoImportacion:
        """Registra los renglones válidos del CSV e informa los rechazados."""
        resultado = ImportadorEnvios(self._fabrica).importar(ruta, self._reloj.ahora())
        for envio in resultado.aceptados:
            self._dar_de_alta(envio)
        self.guardar()
        return resultado

    # ----- 6. reporte ------------------------------------------------------
    def generar_reporte(self, fecha: date, ruta: str) -> str:
        """Escribe el reporte del día y regresa su texto."""
        generador = GeneradorReporte()
        reporte = generador.construir(fecha, self._registro.todos())
        generador.escribir(reporte, ruta)
        return reporte.texto()

    # ----- 8. simulación ---------------------------------------------------
    def simular_jornada(self, ruta_bitacora: str | None = None, semilla: int | None = None,
                        prob_fallo: float = 0.10) -> ResumenJornada:
        """Todos los repartidores reparten a la vez; la central muestra el avance."""
        central = CentralMonitoreo()
        central.suscribir(VistaConsola())
        if ruta_bitacora:
            central.suscribir(BitacoraArchivo(ruta_bitacora))
        simulador = SimuladorJornada(self._repartidores, central, self._reloj,
                                     prob_fallo=prob_fallo, semilla=semilla)
        try:
            return simulador.ejecutar()
        finally:
            self.guardar()

    # ----- 7. conservar ----------------------------------------------------
    def guardar(self) -> None:
        """Guarda envíos, repartidores y contador de guías."""
        self._repositorio.guardar_envios(self._registro.todos())
        self._repositorio.guardar_repartidores(self._repartidores)
        self._repositorio.guardar_contador(self._guias.contador)
