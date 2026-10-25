import unittest
import sys
import builtins
from unittest.mock import patch

import pandas as pd

from utilidades.paginacion import paginar_dataframe


class PaginacionTest(unittest.TestCase):
    def test_limita_cada_pagina_a_cincuenta(self):
        datos = pd.DataFrame({"id": range(125), "valor": range(125)})

        pagina, actual, total = paginar_dataframe(datos, 2)

        self.assertEqual(len(pagina), 50)
        self.assertEqual((actual, total), (2, 3))
        self.assertEqual(pagina["id"].tolist(), list(range(50, 100)))

    def test_normaliza_pagina_fuera_de_rango(self):
        datos = pd.DataFrame({"id": range(51)})

        pagina, actual, total = paginar_dataframe(datos, 99)

        self.assertEqual((actual, total), (2, 2))
        self.assertEqual(pagina["id"].tolist(), [50])

    def test_no_altera_dataframe_original(self):
        datos = pd.DataFrame({"valor": range(80)})
        suma_original = datos["valor"].sum()

        paginar_dataframe(datos, 1)

        self.assertEqual(len(datos), 80)
        self.assertEqual(datos["valor"].sum(), suma_original)


class _ResultadoFalso:
    def __init__(self, filas):
        self._filas = filas

    def fetchall(self):
        return self._filas


class _FilaFalsa:
    def __init__(self, **valores):
        self._mapping = valores


class _SesionFalsa:
    def __init__(self):
        self.parametros = None
        self.cerrada = False

    def execute(self, consulta, parametros):
        self.parametros = parametros
        return _ResultadoFalso(
            [_FilaFalsa(id_resultado=1, id_carga=parametros["lote"])]
        )

    def close(self):
        self.cerrada = True


class DashboardQueryTest(unittest.TestCase):
    def test_consulta_solo_el_lote_solicitado(self):
        from vistas.vista_panel_principal import _cargar_datos_dashboard

        sesion = _SesionFalsa()
        with patch(
            "vistas.vista_panel_principal.obtener_session",
            return_value=sesion,
        ):
            datos = _cargar_datos_dashboard(7)

        self.assertEqual(sesion.parametros, {"lote": 7})
        self.assertEqual(datos["id_carga"].tolist(), [7])
        self.assertTrue(sesion.cerrada)


class DashboardPaginationTest(unittest.TestCase):
    def test_limita_ambas_secciones_sin_recortar_datos_analiticos(self):
        from vistas.vista_panel_principal import _preparar_paginas_dashboard

        datos = pd.DataFrame(
            {
                "id_resultado": range(125),
                "puntaje_riesgo": range(125),
            }
        )

        matriz, casos, meta = _preparar_paginas_dashboard(datos, 1, 3)

        self.assertEqual(len(matriz), 50)
        self.assertEqual(len(casos), 25)
        self.assertEqual(meta, {"matriz": (1, 3), "casos": (3, 3)})
        self.assertEqual(len(datos), 125)
        self.assertEqual(datos["puntaje_riesgo"].sum(), 7750)


class LazyImportsTest(unittest.TestCase):
    def test_resuelve_solo_la_vista_solicitada(self):
        from utilidades.enrutador_vistas import resolver_vista

        modulos_pesados = {
            "vistas.vista_carga_datos",
            "vistas.vista_detalle_auditoria",
            "vistas.vista_estadisticas_globales",
        }
        for modulo in modulos_pesados:
            sys.modules.pop(modulo, None)

        funcion = resolver_vista("vista_estadisticas_globales")

        self.assertEqual(funcion.__name__, "renderizar_vista_estadisticas")
        self.assertIn("vistas.vista_estadisticas_globales", sys.modules)
        self.assertNotIn("vistas.vista_carga_datos", sys.modules)
        self.assertNotIn("vistas.vista_detalle_auditoria", sys.modules)


class ExpedienteQueryTest(unittest.TestCase):
    def test_relaciones_se_aislan_por_lote_y_ruc(self):
        from vistas.vista_detalle_auditoria import _cargar_relaciones

        sesion = _SesionFalsa()
        with patch(
            "vistas.vista_detalle_auditoria.obtener_session",
            return_value=sesion,
        ):
            datos = _cargar_relaciones(4, "20100012345")

        self.assertEqual(
            sesion.parametros,
            {"lote": 4, "ruc": "20100012345"},
        )
        self.assertEqual(len(datos), 1)
        self.assertTrue(sesion.cerrada)

    def test_grafo_reutiliza_disposicion_para_los_mismos_datos(self):
        from vistas.vista_detalle_auditoria import _construir_grafo_cacheado

        relaciones = pd.DataFrame(
            {
                "id_convocatoria": [1],
                "entidad_ruc": ["20100012345"],
            }
        )
        _construir_grafo_cacheado.clear()
        with patch(
            "vistas.vista_detalle_auditoria."
            "construir_grafo_bipartito_fraccionamiento",
            return_value=("figura", "grafo"),
        ) as construir:
            primero = _construir_grafo_cacheado(
                relaciones,
                "20100012345",
            )
            segundo = _construir_grafo_cacheado(
                relaciones,
                "20100012345",
            )

        self.assertEqual(primero, segundo)
        self.assertEqual(construir.call_count, 1)


class ExplicabilidadTest(unittest.TestCase):
    def test_modo_proporcional_no_intenta_importar_shap(self):
        from modulos_ia.explicabilidad_ia import calcular_explicabilidad_caso

        importaciones = []
        importar_real = builtins.__import__

        def registrar_importacion(nombre, *args, **kwargs):
            importaciones.append(nombre)
            return importar_real(nombre, *args, **kwargs)

        caso = {
            "similitud_nlp": 0.8,
            "monto_acumulado_30d": 50000,
            "frecuencia_compras_30d": 3,
            "dias_desde_compra_anterior": 5,
        }
        with patch("builtins.__import__", side_effect=registrar_importacion):
            resultado = calcular_explicabilidad_caso(caso)

        self.assertNotIn("shap", importaciones)
        self.assertEqual(len(resultado), 4)
        self.assertAlmostEqual(
            float(resultado["impacto_porcentaje"].sum()),
            100.0,
            places=1,
        )


if __name__ == "__main__":
    unittest.main()
