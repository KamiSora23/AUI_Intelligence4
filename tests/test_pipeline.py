import io
import unittest
from pathlib import Path

import pandas as pd

from modulos_ia.extractor_caracteristicas import (
    extraer_caracteristicas_temporales_y_nlp,
)
from modulos_ia.modelo_aislamiento import procesar_estado_revision
from utilidades.estados_revision import (
    describir_estado_revision,
    explicar_estado_revision,
    nivel_de_puntaje,
    texto_separacion,
    texto_ventana,
    titulo_informe,
    ventana_desde_explicaciones,
)
from utilidades.exportador_resultados import (
    COLUMNAS_METRICAS,
    COLUMNAS_RESULTADOS,
    COLUMNAS_UMBRALES,
    construir_excel_resultados,
)
from utilidades.mapeador_columnas import normalizar_y_emparejar_columnas
from vistas.vista_carga_datos import (
    _etiqueta_referencia,
    _nivel_riesgo,
    evaluar_estado_segun_flujo,
    leer_csv_con_codificacion,
)


class NormalizacionTest(unittest.TestCase):
    def test_mapea_encabezados_comunes(self):
        fuente = pd.DataFrame(
            {
                "RUC Entidad": ["20100012345"],
                "Nombre Entidad": ["ENTIDAD DE PRUEBA"],
                "Objeto Contratacion": ["SERVICIO DE PRUEBA"],
                "Valor Referencial": [12500.0],
                "Fecha Publicacion": ["2026-01-10"],
            }
        )

        resultado = normalizar_y_emparejar_columnas(fuente)

        for columna in (
            "entidad_ruc",
            "entidad_nombre",
            "descripcion_item",
            "monto_referencial",
            "fecha_convocatoria",
        ):
            self.assertIn(columna, resultado.columns)

    def test_filas_vacias_no_cuentan_como_sin_fecha(self):
        # Como en Dataset_Contraloria (1).xlsx: filas en blanco al final y una
        # con solo un resto de fórmula en la etiqueta.
        fuente = pd.DataFrame(
            {
                "RUC Entidad": ["20100012345", "20100012345", None, None],
                "Nombre Entidad": ["ENTIDAD", "ENTIDAD", None, None],
                "Objeto Contratacion": ["SERVICIO A", "SERVICIO B", None, None],
                "Valor Referencial": [1000.0, 2000.0, None, None],
                "Fecha Publicacion": ["2026-01-10", None, None, None],
                "es_fraccionamiento": [1, 0, None, 0],
            }
        )

        resultado = normalizar_y_emparejar_columnas(fuente)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.attrs["filas_vacias"], 2)
        # La compra sin fecha sí se sigue informando como omitida.
        self.assertEqual(resultado.attrs["filas_omitidas_fecha"], 1)

    def test_limpia_ruc_con_decimales_y_codigos(self):
        fuente = pd.DataFrame(
            {
                "RUC Entidad": ["20147617195.0"],
                "Nombre Entidad": ["MUNICIPALIDAD PROVINCIAL DE TACNA"],
                "Objeto Contratacion": ["SERVICIO DE PRUEBA"],
                "Valor Referencial": [2150.0],
                "Fecha Publicacion": ["2019-01-16"],
                "CUBSO": ["80100001.0"],
            }
        )

        resultado = normalizar_y_emparejar_columnas(fuente)
        self.assertEqual(resultado["entidad_ruc"].iloc[0], "20147617195")
        self.assertEqual(resultado["codigo_cubso"].iloc[0], "80100001")

    def test_normaliza_fechas_variados_formatos(self):
        fuente = pd.DataFrame(
            {
                "RUC": ["20156058719", "20156058719"],
                "Entidad": ["PROYECTO CHAVIMOCHIC", "PROYECTO CHAVIMOCHIC"],
                "Descripcion": ["ALQUILER INMUEBLE A", "ALQUILER INMUEBLE B"],
                "Monto": ["S/. 270,000.00", 15000],
                "Fecha Convocatoria": ["19/12/2024", "2024-12-25"],
            }
        )

        resultado = normalizar_y_emparejar_columnas(fuente)
        self.assertEqual(resultado["fecha_convocatoria"].iloc[0], "2024-12-19")
        self.assertEqual(resultado["fecha_convocatoria"].iloc[1], "2024-12-25")
        self.assertEqual(resultado["monto_referencial"].iloc[0], 270000.0)
        self.assertEqual(resultado["monto_referencial"].iloc[1], 15000.0)


class VentanaTemporalTest(unittest.TestCase):
    def setUp(self):
        self.fuente = pd.DataFrame(
            [
                {
                    "entidad_ruc": "20100012345",
                    "entidad_nombre": "ENTIDAD DE PRUEBA",
                    "descripcion_item": "ADQUISICIÓN DE EQUIPOS",
                    "monto_referencial": 25000.0,
                    "fecha_convocatoria": "2026-01-01",
                    "codigo_cubso": "43000000",
                },
                {
                    "entidad_ruc": "20100012345",
                    "entidad_nombre": "ENTIDAD DE PRUEBA",
                    "descripcion_item": "ADQUISICIÓN DE EQUIPOS",
                    "monto_referencial": 26000.0,
                    "fecha_convocatoria": "2026-02-10",
                    "codigo_cubso": "43000000",
                },
            ]
        )

    def test_respeta_ventana_configurada(self):
        resultado_30 = extraer_caracteristicas_temporales_y_nlp(
            self.fuente,
            ventana_dias=30,
        )
        resultado_60 = extraer_caracteristicas_temporales_y_nlp(
            self.fuente,
            ventana_dias=60,
        )

        self.assertEqual(resultado_30["frecuencia_compras_30d"].tolist(), [1, 1])
        self.assertEqual(resultado_60["frecuencia_compras_30d"].tolist(), [2, 2])

    def test_ventana_se_recupera_de_los_motivos_del_motor(self):
        resultado = extraer_caracteristicas_temporales_y_nlp(
            self.fuente,
            ventana_dias=60,
        )

        self.assertEqual(
            ventana_desde_explicaciones(resultado["explicacion_reglas"]),
            60,
        )
        self.assertIsNone(ventana_desde_explicaciones(["Exento o sin indicios"]))
        self.assertEqual(texto_ventana(60), "60 días")
        self.assertEqual(texto_ventana(None), "la ventana")


class EstadoRevisionTest(unittest.TestCase):
    def test_propuestas_indican_que_falta_el_dictamen(self):
        for estado, etiqueta in (
            ("Propuesta_Confirmado", "Propuesta de confirmar"),
            ("Propuesta_Descartado", "Propuesta de descartar"),
        ):
            self.assertEqual(
                describir_estado_revision(estado, con_auditor=False),
                (etiqueta, "Falta el dictamen del auditor"),
            )

    def test_explicacion_separa_riesgo_de_la_decision(self):
        # Caso 6679: 58 puntos (riesgo medio) con propuesta de descartar.
        texto = explicar_estado_revision("Propuesta_Descartado", con_auditor=False)
        self.assertNotIn("bajo riesgo", texto)
        self.assertIn("no sustituye el dictamen del auditor", texto)
        self.assertEqual(nivel_de_puntaje(58.0), "Medio")

    def test_titulo_del_informe_no_es_una_conclusion(self):
        self.assertEqual(
            titulo_informe("Propuesta_Confirmado", False, 81.0),
            "Propuesta de revisión por riesgo alto",
        )
        self.assertEqual(
            titulo_informe("Propuesta_Descartado", False, 58.0),
            "Propuesta del sistema: descartar · riesgo medio",
        )
        self.assertEqual(
            titulo_informe("Confirmado_Fraccionamiento", True, 92.4),
            "Dictamen: fraccionamiento confirmado · riesgo alto",
        )

    def test_separacion_sin_compra_anterior(self):
        self.assertEqual(texto_separacion(999), "Sin compra anterior registrada")
        self.assertEqual(texto_separacion(None), "Sin compra anterior registrada")
        self.assertEqual(texto_separacion(11), "11 días")
        self.assertEqual(texto_separacion(1), "1 día")


class ExportacionExcelTest(unittest.TestCase):
    def _lote(self, etiquetas):
        return pd.DataFrame(
            {
                "id_convocatoria": [1, 2, 3, 4],
                "entidad_ruc": ["20100012345"] * 4,
                "entidad_nombre": ["ENTIDAD DE PRUEBA"] * 4,
                "descripcion_item": ["SERVICIO A", "SERVICIO B", "SERVICIO C", "SERVICIO D"],
                "monto_referencial": [1000, 2000, 3000, 4000],
                "fecha_convocatoria": ["2024-01-01"] * 4,
                "codigo_cubso": ["80100001"] * 4,
                "tipo_proceso": ["Contratación Directa"] * 4,
                "puntaje_riesgo": [80.0, 75.0, 50.0, 10.0],
                "score_reglas_negocio": [80.0, 70.0, 50.0, 10.0],
                "bono_ia": [0.0, 5.0, 0.0, 0.0],
                "nivel_riesgo": ["Alto", "Alto", "Medio", "Bajo"],
                "frecuencia_compras_30d": [3, 2, 1, 1],
                "monto_acumulado_30d": [5000, 4000, 3000, 4000],
                "explicacion_reglas": ["", "", "", ""],
                "estado_revision": ["Propuesta_Confirmado", "Propuesta_Confirmado",
                                    "Propuesta_Descartado", "Propuesta_Descartado"],
                "id_usuario_auditor": [None] * 4,
                "etiqueta_referencia": etiquetas,
            }
        )

    def _columnas(self, contenido):
        return {
            hoja: list(tabla.columns)
            for hoja, tabla in pd.read_excel(io.BytesIO(contenido), sheet_name=None).items()
        }

    def test_con_etiqueta_genera_las_hojas_del_ejemplo(self):
        contenido = construir_excel_resultados(self._lote([1, 0, 1, 0]))
        hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None)

        self.assertEqual(
            self._columnas(contenido),
            {
                "Resultados": COLUMNAS_RESULTADOS,
                "Metricas": COLUMNAS_METRICAS,
                "Umbrales": COLUMNAS_UMBRALES,
                "Errores": COLUMNAS_RESULTADOS + ["tipo_error"],
            },
        )
        self.assertEqual(hojas["Metricas"]["modelo"].tolist(), ["Híbrido", "Solo reglas"])
        # 75 puntos sin fraccionamiento y 50 con fraccionamiento: un error de cada tipo.
        self.assertEqual(
            sorted(hojas["Errores"]["tipo_error"]), ["Falso negativo", "Falso positivo"]
        )

    def test_sin_etiqueta_conserva_el_formato_sin_inventar_metricas(self):
        contenido = construir_excel_resultados(self._lote([None] * 4))
        hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None)

        self.assertEqual(list(hojas), ["Resultados", "Metricas", "Umbrales", "Errores"])
        self.assertEqual(len(hojas["Resultados"]), 4)
        for hoja in ("Metricas", "Umbrales", "Errores"):
            self.assertTrue(hojas[hoja].empty)

    def test_sin_etiqueta_usa_solo_los_dictamenes_del_auditor(self):
        lote = self._lote([None] * 4)
        lote["estado_revision"] = [
            "Confirmado_Fraccionamiento", "Descartado", "Descartado", "Confirmado_Fraccionamiento",
        ]
        # El último no tiene auditor: es una clasificación automática y no cuenta.
        lote["id_usuario_auditor"] = [1, 1, 1, None]
        hojas = pd.read_excel(io.BytesIO(construir_excel_resultados(lote)), sheet_name=None)

        self.assertEqual(hojas["Resultados"]["es_fraccionamiento"].tolist()[:3], [1, 0, 0])
        self.assertTrue(pd.isna(hojas["Resultados"]["es_fraccionamiento"].iloc[3]))
        self.assertEqual(hojas["Metricas"]["modelo"].tolist(), ["Híbrido", "Solo reglas"])
        self.assertEqual(len(hojas["Umbrales"]), 17)

    def test_columnas_coinciden_con_resultados_xlsx_de_ejemplo(self):
        ejemplo = Path(__file__).resolve().parent.parent / "resultados.xlsx"
        if not ejemplo.exists():
            self.skipTest("No está el libro de ejemplo resultados.xlsx")
        esperado = {
            hoja: list(tabla.columns)
            for hoja, tabla in pd.read_excel(ejemplo, sheet_name=None).items()
        }
        contenido = construir_excel_resultados(self._lote([1, 0, 1, 0]))
        self.assertEqual(self._columnas(contenido), esperado)


class EstadoSegunFlujoTest(unittest.TestCase):
    def test_ingesta_usa_los_mismos_tramos_que_el_modelo(self):
        puntajes = [71.0, 55.0, 41.0, 40.99]
        datos = pd.DataFrame({"puntaje_riesgo": puntajes})
        esperado = procesar_estado_revision(datos, modo_automatico=True)["estado_revision"].tolist()
        for flujo in ("Automático", "Semiautomático"):
            self.assertEqual(
                [evaluar_estado_segun_flujo(p, 71.0, flujo) for p in puntajes], esperado
            )
        self.assertEqual(esperado, [
            "Propuesta_Confirmado", "Pendiente", "Pendiente", "Propuesta_Descartado",
        ])
        self.assertEqual(evaluar_estado_segun_flujo(90.0, 71.0, "Manual"), "Pendiente")


class EtiquetaReferenciaTest(unittest.TestCase):
    def test_acepta_numeros_y_texto_de_caso_esperado(self):
        for valor, esperado in (
            (1, 1), (0.0, 0), ("1", 1), ("FRACCIONAMIENTO", 1), ("normal", 0),
            ("Sí", 1), ("No", 0), (None, None), ("", None), ("DUDOSO", None), (2, None),
        ):
            self.assertEqual(
                _etiqueta_referencia({"es_fraccionamiento": valor}), esperado, valor
            )


class LecturaCsvTest(unittest.TestCase):
    def test_acepta_utf8_y_windows_1252(self):
        contenido = "descripcion\nCONTRATACIÓN DEL SERVICIO\n"
        for codificacion in ("utf-8-sig", "cp1252"):
            datos = leer_csv_con_codificacion(io.BytesIO(contenido.encode(codificacion)))
            self.assertEqual(datos["descripcion"].iloc[0], "CONTRATACIÓN DEL SERVICIO")

    def test_dictamen_solo_si_lo_registro_un_auditor(self):
        self.assertEqual(
            describir_estado_revision("Descartado", con_auditor=True)[0],
            "Dictamen: descartado",
        )
        self.assertEqual(
            describir_estado_revision("Confirmado_Fraccionamiento", con_auditor=False)[0],
            "Clasificación automática: fraccionamiento confirmado",
        )
        self.assertEqual(
            describir_estado_revision(None, con_auditor=False)[0],
            "Pendiente de revisión",
        )


class ClasificacionTest(unittest.TestCase):
    def test_limites_de_riesgo(self):
        self.assertEqual(_nivel_riesgo(71.0), "Alto")
        self.assertEqual(_nivel_riesgo(41.0), "Medio")
        self.assertEqual(_nivel_riesgo(40.99), "Bajo")

    def test_estado_automatico_utiliza_los_mismos_limites(self):
        datos = pd.DataFrame({"puntaje_riesgo": [71.0, 41.0, 40.99]})
        resultado = procesar_estado_revision(datos, modo_automatico=True)

        self.assertEqual(
            resultado["estado_revision"].tolist(),
            ["Propuesta_Confirmado", "Pendiente", "Propuesta_Descartado"],
        )


if __name__ == "__main__":
    unittest.main()
