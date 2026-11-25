"""Pruebas de tarifas, tipos de envío y reglas de validación (función 1)."""

import unittest

from paqueteria.excepciones.errores import DatoInvalidoError, EnvioNoPermitidoError
from tests.utilidades import FABRICA, TARIFAS, datos


class PruebasCotizacion(unittest.TestCase):

    def test_sobre_tarifa_fija(self):
        envio = FABRICA.crear(datos(tipo="sobre", destinatario_cp="53000"))
        self.assertEqual(envio.cotizar(TARIFAS).total, 90)

    def test_paquete_usa_peso_real_si_es_mayor(self):
        envio = FABRICA.crear(datos())          # real 3 kg, volumétrico 1.8 kg
        self.assertEqual(envio.cotizar(TARIFAS).total, 3 * 25)

    def test_paquete_usa_peso_volumetrico_si_es_mayor(self):
        envio = FABRICA.crear(datos(peso_kg="1", largo_cm="50", ancho_cm="40", alto_cm="30"))
        self.assertAlmostEqual(envio.cotizar(TARIFAS).total, 12 * 25)   # 60000/5000 = 12 kg

    def test_fragil_express_orden_del_calculo(self):
        envio = FABRICA.crear(datos(tipo="fragil", servicio="express", destinatario_cp="44100",
                                    peso_kg="2", largo_cm="40", ancho_cm="30", alto_cm="20",
                                    valor_declarado="1000"))
        c = envio.cotizar(TARIFAS)
        self.assertEqual(c.base, 312.0)               # 4.8 kg × 65
        self.assertEqual(c.recargo_fragil, 62.4)      # 20 %
        self.assertEqual(c.recargo_servicio, 187.2)   # 50 % de (base + frágil)
        self.assertEqual(c.seguro, 30.0)              # 3 % de 1000, sin recargo express
        self.assertEqual(c.total, 591.6)
        self.assertEqual(envio.total(), 591.6)

    def test_refrigerado_solo_express(self):
        with self.assertRaises(EnvioNoPermitidoError):
            FABRICA.crear(datos(tipo="refrigerado", servicio="estandar"))

    def test_refrigerado_no_a_zona_nacional(self):
        with self.assertRaises(EnvioNoPermitidoError):
            FABRICA.crear(datos(tipo="refrigerado", servicio="express", destinatario_cp="44100"))

    def test_refrigerado_express_local_si_se_permite(self):
        envio = FABRICA.crear(datos(tipo="refrigerado", servicio="express"))
        self.assertEqual(envio.tipo(), "Paquete refrigerado")

    def test_datos_invalidos(self):
        casos = [dict(peso_kg="-1"), dict(peso_kg="abc"), dict(destinatario_cp="99999"),
                 dict(destinatario_cp="123"), dict(tipo="caja"), dict(servicio="urgente"),
                 dict(destinatario_nombre=""), dict(remitente_telefono="123"),
                 dict(valor_declarado="0"), dict(alto_cm="0")]
        for cambio in casos:
            with self.subTest(cambio=cambio), self.assertRaises(DatoInvalidoError):
                FABRICA.crear(datos(**cambio))

    def test_tipo_acepta_acentos_y_mayusculas(self):
        self.assertEqual(FABRICA.crear(datos(tipo="Paquete Frágil")).tipo(), "Paquete frágil")


if __name__ == "__main__":
    unittest.main()
