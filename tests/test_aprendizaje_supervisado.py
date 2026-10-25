import unittest

import numpy as np
import pandas as pd

from modulos_ia.aprendizaje_supervisado import (
    MIN_ENTIDADES_NEGATIVAS,
    aplicar,
    casos_de_referencia,
    entrenar,
    matriz_variables,
    probabilidad_a_puntaje,
    validar,
)


def _casos(n_entidades, filas_por_entidad, semilla=0, senal=True):
    """Casos sintéticos: la etiqueta depende de la similitud, no de las reglas."""
    rng = np.random.default_rng(semilla)
    filas = []
    for e in range(n_entidades):
        for k in range(filas_por_entidad):
            similitud = rng.uniform(0, 1)
            etiqueta = int(similitud > 0.5) if senal else int(rng.uniform() > 0.5)
            filas.append({
                "id_resultado": len(filas) + 1,
                "entidad_ruc": f"20{e:09d}",
                "descripcion_item": f"COMPRA {e}-{k}",
                "monto_referencial": float(rng.uniform(1_000, 50_000)),
                "fecha_convocatoria": "2024-01-01",
                "frecuencia_compras_30d": int(rng.integers(1, 5)),
                "similitud_nlp": similitud,
                "monto_acumulado_30d": float(rng.uniform(1_000, 100_000)),
                "dias_desde_compra_anterior": int(rng.integers(1, 365)),
                # Las reglas no tienen relación con la etiqueta.
                "score_reglas_negocio": float(rng.choice([0.0, 55.0, 80.0])),
                "bono_ia": 0.0,
                "estado_revision": "Propuesta_Descartado",
                "id_usuario_auditor": None,
                "etiqueta_referencia": etiqueta,
                "explicacion_reglas": "Motivos",
            })
    return casos_de_referencia(pd.DataFrame(filas))


class AprendizajeSupervisadoTest(unittest.TestCase):
    def test_inactivo_no_cambia_ningun_resultado(self):
        resultados = _casos(3, 5)
        pd.testing.assert_frame_equal(aplicar(resultados, None), resultados)

    def test_con_pocos_datos_no_se_puede_activar(self):
        # Como hoy: pocos conformes y de pocas entidades.
        validacion = validar(_casos(4, 8))
        self.assertFalse(validacion.suficiente)
        self.assertFalse(validacion.supera)
        self.assertIn("Faltan", validacion.motivo)

    def test_sin_senal_no_supera_aunque_haya_datos(self):
        # Con la regla anterior (solo margen) estas semillas se activaban por azar.
        for semilla in (0, 1, 4):
            validacion = validar(_casos(MIN_ENTIDADES_NEGATIVAS + 4, 14, semilla=semilla, senal=False))
            self.assertTrue(validacion.suficiente)
            self.assertFalse(validacion.supera, semilla)

    def test_con_senal_real_supera_y_puntua_coherente(self):
        casos = _casos(MIN_ENTIDADES_NEGATIVAS + 4, 14, semilla=2)
        validacion = validar(casos)
        self.assertTrue(validacion.supera, validacion)
        self.assertGreater(
            validacion.modelo["exactitud_balanceada"], validacion.actual["exactitud_balanceada"]
        )

        modelo = entrenar(casos)
        puntuados = aplicar(casos, modelo)
        probabilidad = modelo.predict_proba(matriz_variables(casos))[:, 1]
        np.testing.assert_array_equal(puntuados["puntaje_riesgo"] >= 71, probabilidad >= 0.5)
        self.assertTrue((puntuados["nivel_riesgo"][puntuados["puntaje_riesgo"] >= 71] == "Alto").all())
        # Se conservan las reglas y se documenta el puntaje anterior.
        pd.testing.assert_series_equal(puntuados["score_reglas_negocio"], casos["score_reglas_negocio"])
        self.assertIn("Aprendizaje supervisado: probabilidad", puntuados["explicacion_reglas"].iloc[0])

    def test_escala_de_probabilidad_a_puntaje(self):
        self.assertEqual(probabilidad_a_puntaje([0.0, 0.5, 1.0]).tolist(), [0.0, 71.0, 100.0])
        valores = probabilidad_a_puntaje(np.linspace(0, 1, 21))
        self.assertTrue((np.diff(valores) > 0).all())

    def test_referencia_sin_duplicados_y_con_prioridad_del_dictamen(self):
        base = {
            "entidad_ruc": "20100012345", "descripcion_item": "SERVICIO A",
            "monto_referencial": 1000.0, "fecha_convocatoria": "2024-01-01",
        }
        filas = pd.DataFrame([
            # La misma compra cargada en tres lotes.
            {**base, "id_resultado": 1, "etiqueta_referencia": 1, "estado_revision": "Propuesta_Confirmado", "id_usuario_auditor": None},
            {**base, "id_resultado": 2, "etiqueta_referencia": 1, "estado_revision": "Descartado", "id_usuario_auditor": 7},
            {**base, "id_resultado": 3, "etiqueta_referencia": 1, "estado_revision": "Propuesta_Confirmado", "id_usuario_auditor": None},
            # Una propuesta sin etiqueta ni dictamen no es un caso de referencia.
            {**base, "descripcion_item": "SERVICIO B", "id_resultado": 4, "etiqueta_referencia": None,
             "estado_revision": "Propuesta_Confirmado", "id_usuario_auditor": None},
        ])
        casos = casos_de_referencia(filas)
        self.assertEqual(len(casos), 1)
        self.assertEqual(casos["referencia"].iloc[0], 0)  # prevalece el dictamen del auditor

    def test_excluye_resumenes_de_hallazgo_de_lotes_antiguos(self):
        filas = pd.DataFrame([
            {"id_resultado": 1, "entidad_ruc": "20100012345", "monto_referencial": 0.0,
             "fecha_convocatoria": "2024-01-01", "etiqueta_referencia": 1,
             "estado_revision": "Propuesta_Confirmado", "id_usuario_auditor": None,
             # Lote antiguo: el CUBSO quedó como código numérico.
             "descripcion_item": "Fraccionamiento en la contratación de combustible",
             "codigo_cubso": "993"},
            {"id_resultado": 2, "entidad_ruc": "20100012345", "monto_referencial": 900.0,
             "fecha_convocatoria": "2024-01-01", "etiqueta_referencia": 1,
             "estado_revision": "Propuesta_Confirmado", "id_usuario_auditor": None,
             "descripcion_item": "SERVICIO DE LIMPIEZA", "codigo_cubso": "SERVICIO DE LIMPIEZA"},
        ])
        self.assertEqual(casos_de_referencia(filas)["descripcion_item"].tolist(), ["SERVICIO DE LIMPIEZA"])


if __name__ == "__main__":
    unittest.main()
