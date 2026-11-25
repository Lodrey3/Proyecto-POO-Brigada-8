"""Pruebas de asignación, importación, persistencia, reporte y simulación (funciones 4 a 8)."""

import json
import os
import shutil
import tempfile
import threading
import unittest
from datetime import timedelta

from paqueteria.concurrencia.central import CentralMonitoreo
from paqueteria.concurrencia.simulador import SimuladorJornada
from paqueteria.excepciones.errores import ArchivoCorruptoError, ArchivoNoEncontradoError, CapacidadExcedidaError
from paqueteria.modelo.repartidor import Repartidor
from paqueteria.modelo.vehiculo import Camioneta, Motocicleta
from paqueteria.persistencia.repositorio_json import RepositorioJSON
from paqueteria.persistencia.serializador import SerializadorEnvios
from paqueteria.servicios.asignador import AsignadorEnvios
from paqueteria.servicios.guias import GeneradorGuias
from paqueteria.servicios.importador import ImportadorEnvios
from paqueteria.servicios.reportes import GeneradorReporte
from paqueteria.util.reloj import RelojSimulado
from tests.utilidades import FABRICA, FECHA, envio_registrado

H = timedelta(hours=1)
DATOS = os.path.join(os.path.dirname(__file__), "..", "datos")


def en_almacen(guia, peso):
    envio = envio_registrado(guia, peso_kg=str(peso))
    envio.ingresar_a_almacen(FECHA + H)
    return envio


class PruebasAsignacion(unittest.TestCase):

    def test_no_excede_capacidad(self):
        moto = Repartidor("R01", "Ana", Motocicleta())
        envios = [en_almacen(f"G{i}", 8) for i in range(4)]     # 32 kg, la moto carga 20
        resultado = AsignadorEnvios().asignar(envios, [moto])
        self.assertEqual(len(resultado.asignados["R01"]), 2)
        self.assertEqual(len(resultado.sin_asignar), 2)
        self.assertLessEqual(moto.carga_actual(), 20)

    def test_asignar_directo_lanza_si_no_cabe(self):
        moto = Repartidor("R01", "Ana", Motocicleta())
        with self.assertRaises(CapacidadExcedidaError):
            moto.asignar(en_almacen("G1", 25))

    def test_pesados_van_a_camioneta(self):
        moto, cam = Repartidor("R01", "Ana", Motocicleta()), Repartidor("R03", "Carla", Camioneta())
        resultado = AsignadorEnvios().asignar([en_almacen("G1", 120)], [moto, cam])
        self.assertEqual(resultado.asignados, {"R03": ["G1"]})


class PruebasImportacion(unittest.TestCase):

    def test_archivo_de_ejemplo_con_errores(self):
        resultado = ImportadorEnvios(FABRICA).importar(
            os.path.join(DATOS, "envios_con_errores.csv"), FECHA)
        # Con las zonas de prueba solo el CP 03100 es local: el sobre a Ana Torres pasa.
        self.assertTrue(resultado.rechazados)
        self.assertTrue(all(r.motivo for r in resultado.rechazados))
        self.assertEqual(resultado.rechazados[0].numero, 3)

    def test_archivo_faltante_y_danado(self):
        with self.assertRaises(ArchivoNoEncontradoError):
            ImportadorEnvios(FABRICA).importar("no_existe.csv", FECHA)
        with self.assertRaises(ArchivoCorruptoError):
            ImportadorEnvios(FABRICA).importar(os.path.join(DATOS, "envios_danado.csv"), FECHA)


class PruebasPersistencia(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.repo = RepositorioJSON(self.dir, SerializadorEnvios(FABRICA))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_ida_y_vuelta_conserva_historial(self):
        envio = en_almacen("PQ-20261120-0001", 3)
        envio.salir_a_ruta(FECHA + 2 * H)
        envio.registrar_intento_fallido(FECHA + 3 * H)
        self.repo.guardar_envios([envio])
        self.repo.guardar_contador(7)
        cargado = self.repo.cargar_envios()[0]
        self.assertEqual(cargado.guia, envio.guia)
        self.assertEqual(cargado.estado.nombre, "EnAlmacen")
        self.assertEqual(cargado.intentos_fallidos, 1)
        self.assertEqual(cargado.historial(), envio.historial())
        self.assertEqual(cargado.total(), envio.total())
        self.assertEqual(self.repo.cargar_contador(), 7)

    def test_primera_ejecucion_regresa_vacio(self):
        self.assertEqual(self.repo.cargar_envios(), [])
        self.assertEqual(self.repo.cargar_contador(), 0)

    def test_archivo_danado(self):
        with open(os.path.join(self.dir, "envios.json"), "w") as f:
            f.write("{roto")
        with self.assertRaises(ArchivoCorruptoError):
            self.repo.cargar_envios()

    def test_repartidores_obligatorios(self):
        with self.assertRaises(ArchivoNoEncontradoError):
            RepositorioJSON(self.dir, obligatorio=True).cargar_repartidores()
        with open(os.path.join(self.dir, "repartidores.json"), "w") as f:
            json.dump([{"id": "R1", "nombre": "X", "vehiculo": "avion"}], f)
        with self.assertRaises(ArchivoCorruptoError):
            self.repo.cargar_repartidores()


class PruebasConcurrencia(unittest.TestCase):

    def test_guias_unicas_con_hilos(self):
        generador, guias, lock = GeneradorGuias(), [], threading.Lock()

        def pedir():
            for _ in range(200):
                g = generador.siguiente(FECHA.date())
                with lock:
                    guias.append(g)
        hilos = [threading.Thread(target=pedir) for _ in range(8)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(len(guias), len(set(guias)))
        self.assertEqual(generador.contador, 1600)

    def test_jornada_consistente(self):
        repartidores = [Repartidor("R01", "Ana", Camioneta()), Repartidor("R02", "Beto", Camioneta())]
        envios = [en_almacen(f"G{i:02d}", 2) for i in range(20)]
        AsignadorEnvios().asignar(envios, repartidores)
        resumen = SimuladorJornada(repartidores, CentralMonitoreo(), RelojSimulado(FECHA + 2 * H),
                                   prob_fallo=0.5, semilla=1, pausa_max=0.01).ejecutar()
        finales = [e.estado.nombre for e in envios]
        self.assertTrue(all(estado in ("Entregado", "Devuelto") for estado in finales))
        self.assertEqual(resumen.entregados, finales.count("Entregado"))
        self.assertEqual(resumen.devueltos, finales.count("Devuelto"))
        for envio in envios:
            if envio.estado.nombre == "Devuelto":
                self.assertEqual(envio.intentos_fallidos, 3)

    def test_reporte(self):
        envio = en_almacen("G1", 3)
        envio.salir_a_ruta(FECHA + 2 * H)
        envio.entregar(FECHA + 3 * H)
        envio.asignar_repartidor("R01")
        reporte = GeneradorReporte().construir(FECHA.date(), [envio])
        self.assertEqual(reporte.por_estado, {"Entregado": 1})
        self.assertEqual(reporte.ingresos_por_tipo, {"Paquete": 75.0})
        self.assertEqual(reporte.entregas_por_repartidor, {"R01": 1})


if __name__ == "__main__":
    unittest.main()
