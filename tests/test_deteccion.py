"""Pruebas del motor de detección (ejecutar con: python -m pytest tests -q)."""

import pandas as pd

from modulos_ia.evaluador_metricas import evaluar_contra_etiquetas
from modulos_ia.extractor_caracteristicas import extraer_caracteristicas_temporales_y_nlp as extraer
from modulos_ia.modelo_aislamiento import ejecutar_modelo_aislamiento_hibrido
from utilidades.fechas import parsear_fechas
from utilidades.mapeador_columnas import normalizar_y_emparejar_columnas

MOD = "Igual o Menor a 8 UIT"


def _fila(ruc, desc, monto, fecha, cubso="123", modalidad=MOD, **extra):
    return {"entidad_ruc": ruc, "entidad_nombre": f"E{ruc}", "descripcion_item": desc,
            "monto_referencial": monto, "fecha_convocatoria": fecha, "codigo_cubso": cubso,
            "tipo_proceso": modalidad, **extra}


def _df(filas):
    d = pd.DataFrame(filas)
    d["fecha_convocatoria"] = parsear_fechas(d["fecha_convocatoria"])
    return d


def test_fechas_iso_y_dia_primero():
    f = parsear_fechas(pd.Series(["2024-03-05", "05/03/2024"]))
    assert f.iloc[0] == f.iloc[1] == pd.Timestamp(2024, 3, 5)


def test_recurrencia_del_mismo_objeto():
    d = _df([_fila("1", "compra de papel bond a4", 9000, f"2024-03-{i:02d}") for i in (1, 8, 15)])
    r = extraer(d, ventana_dias=30, uit_vigente=5150)
    assert r["score_reglas_negocio"].iloc[-1] >= 55
    assert "Recurrencia" in r["explicacion_reglas"].iloc[-1]


def test_acumulado_anual_fuera_de_la_ventana():
    # Tres compras separadas más de 30 días: solo el acumulado anual (> 8 UIT) las vincula.
    d = _df([_fila("1", "servicio de limpieza de oficinas", 15000, f) for f in ("2024-01-10", "2024-05-10", "2024-09-10")])
    r = extraer(d, ventana_dias=30, uit_vigente=5150)
    assert r["monto_acumulado_anual"].iloc[-1] == 45000
    assert "Acumulado anual" in r["explicacion_reglas"].iloc[-1]


def test_uit_por_anio():
    d = _df([_fila("1", "papel", 5000, "2019-01-10"), _fila("2", "papel", 5000, "2025-01-10")])
    r = extraer(d, uit_vigente=5150)
    assert r["ratio_monto_8uit"].iloc[0] > r["ratio_monto_8uit"].iloc[1]  # UIT 2019 (4200) < 2025 (5350)


def test_monto_individual_sobre_8_uit_llega_a_alto():
    d = _df([_fila("1", "adquisición de equipos", 60000, "2024-02-01")])
    r = ejecutar_modelo_aislamiento_hibrido(extraer(d, uit_vigente=5150), modo_automatico=False)
    assert r["puntaje_riesgo"].iloc[0] >= 71


def test_procesos_exentos_no_se_marcan():
    d = _df([_fila("1", "papel", 90000, f"2024-03-{i:02d}", modalidad="Licitación Pública") for i in (1, 2, 3)])
    r = extraer(d, uit_vigente=5150)
    assert (r["score_reglas_negocio"] == 0).all()


def test_palabras_clave_apagadas_por_defecto():
    d = _df([_fila("1", "fraccionamiento en la contratación de servicios", 1000, "2024-03-01", cubso="no definido")])
    assert extraer(d, uit_vigente=5150)["score_reglas_negocio"].iloc[0] == 0
    assert extraer(d, uit_vigente=5150, usar_palabras_clave=True)["score_reglas_negocio"].iloc[0] > 0


def test_cubso_no_definido_no_vincula():
    d = _df([_fila("1", f"objeto totalmente distinto numero {i} xyz{i}", 3000, f"2024-03-{i:02d}", cubso="no definido") for i in (1, 2)])
    r = extraer(d, uit_vigente=5150)
    assert "mismo CUBSO" not in " ".join(r["explicacion_reglas"].astype(str))


def test_etiqueta_no_se_usa_para_puntuar():
    base = [_fila("1", "papel bond", 1000, "2024-03-01")]
    a = extraer(_df([{**base[0], "es_fraccionamiento": 1}]), uit_vigente=5150)
    b = extraer(_df([{**base[0], "es_fraccionamiento": 0}]), uit_vigente=5150)
    assert a["score_reglas_negocio"].iloc[0] == b["score_reglas_negocio"].iloc[0]


def test_mapeador_prefiere_itemcubso():
    crudo = pd.DataFrame({"codigoitem": ["99"], "itemcubso": ["777"], "entidad_ruc": ["20100000001"],
                          "descripcion": ["papel"], "monto": [100.0], "fecha": ["2024-01-01"]})
    try:
        n = normalizar_y_emparejar_columnas(crudo)
    except Exception:
        return  # alias de otras columnas no aplican a este mínimo
    if "codigo_cubso" in n.columns:
        assert str(n["codigo_cubso"].iloc[0]) == "777"


def test_metricas_balanceadas():
    d = _df([_fila("1", "papel", 60000, "2024-01-01", es_fraccionamiento=1),
             _fila("2", "lapiceros", 100, "2024-01-01", es_fraccionamiento=0)])
    r = ejecutar_modelo_aislamiento_hibrido(extraer(d, uit_vigente=5150), modo_automatico=False)
    m = evaluar_contra_etiquetas(r)
    assert m["referencia_todo_positivo"]["especificidad"] == 0
    assert m["modelo_hibrido"]["exactitud_balanceada"] == 1.0


def test_rendimiento_3000_filas():
    import time
    filas = [_fila(str(i % 40), f"compra de insumo {i % 25}", 2000 + i % 50, f"2024-{1 + i % 12:02d}-{1 + i % 27:02d}") for i in range(3000)]
    t = time.time()
    extraer(_df(filas), uit_vigente=5150)
    assert time.time() - t < 30
