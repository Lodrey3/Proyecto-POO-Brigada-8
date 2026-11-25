"""Pruebas del ciclo de vida de un envío (funciones 2 y 3)."""

import unittest
from datetime import timedelta

from paqueteria.excepciones.errores import (
    CancelacionNoPermitidaError,
    DatoInvalidoError,
    TransicionInvalidaError,
)
from paqueteria.modelo.estados import EstadoEnvio
from tests.utilidades import FECHA, envio_registrado

H = timedelta(hours=1)


class PruebasEstados(unittest.TestCase):

    def test_camino_feliz_con_historial(self):
        envio = envio_registrado()
        envio.ingresar_a_almacen(FECHA + H)
        envio.salir_a_ruta(FECHA + 2 * H)
        envio.entregar(FECHA + 3 * H)
        self.assertEqual(envio.estado.nombre, "Entregado")
        self.assertEqual([r.estado for r in envio.historial()],
                         ["Registrado", "EnAlmacen", "EnRuta", "Entregado"])
        self.assertEqual(envio.historial()[-1].fecha_hora, FECHA + 3 * H)

    def test_tres_intentos_fallidos_devuelve(self):
        envio = envio_registrado()
        envio.ingresar_a_almacen(FECHA + H)
        for i in range(1, 4):
            envio.salir_a_ruta(FECHA + 2 * i * H)
            envio.registrar_intento_fallido(FECHA + (2 * i + 1) * H)
            esperado = "EnAlmacen" if i < 3 else "Devuelto"
            self.assertEqual(envio.estado.nombre, esperado)
        self.assertEqual(envio.intentos_fallidos, 3)
        self.assertTrue(envio.estado.es_final())

    def test_transiciones_invalidas(self):
        envio = envio_registrado()
        with self.assertRaises(TransicionInvalidaError):
            envio.entregar(FECHA + H)
        with self.assertRaises(TransicionInvalidaError):
            envio.salir_a_ruta(FECHA + H)

    def test_cancelar_antes_de_ruta(self):
        envio = envio_registrado()
        envio.ingresar_a_almacen(FECHA + H)
        envio.cancelar(FECHA + 2 * H)
        self.assertEqual(envio.estado.nombre, "Cancelado")

    def test_no_se_cancela_en_ruta_ni_final(self):
        envio = envio_registrado()
        envio.ingresar_a_almacen(FECHA + H)
        envio.salir_a_ruta(FECHA + 2 * H)
        with self.assertRaises(CancelacionNoPermitidaError):
            envio.cancelar(FECHA + 3 * H)
        envio.entregar(FECHA + 3 * H)
        with self.assertRaises(CancelacionNoPermitidaError):
            envio.cancelar(FECHA + 4 * H)

    def test_fecha_anterior_se_rechaza(self):
        envio = envio_registrado()
        with self.assertRaises(DatoInvalidoError):
            envio.ingresar_a_almacen(FECHA - H)

    def test_historial_no_se_modifica_desde_fuera(self):
        envio = envio_registrado()
        self.assertIsInstance(envio.historial(), tuple)

    def test_desde_nombre(self):
        self.assertEqual(EstadoEnvio.desde_nombre("EnRuta").nombre, "EnRuta")
        with self.assertRaises(DatoInvalidoError):
            EstadoEnvio.desde_nombre("Perdido")


if __name__ == "__main__":
    unittest.main()
