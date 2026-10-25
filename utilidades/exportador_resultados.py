"""Exporta los resultados de un lote a Excel con el formato de ``resultados.xlsx``."""

from __future__ import annotations

import io

import pandas as pd

from modulos_ia.evaluador_metricas import (
    UMBRAL_ALTO,
    barrido_de_umbrales,
    evaluar_contra_etiquetas,
)

# Hojas, columnas y orden exactos del libro de ejemplo ``resultados.xlsx``.
COLUMNAS_RESULTADOS = [
    "entidad_ruc", "entidad_nombre", "descripcion_item", "monto_referencial",
    "fecha_convocatoria", "codigo_cubso", "tipo_proceso", "es_fraccionamiento",
    "puntaje_riesgo", "score_reglas_negocio", "bono_ia", "nivel_riesgo",
    "frecuencia_compras_30d", "monto_acumulado_30d", "explicacion_reglas",
]
COLUMNAS_METRICAS = [
    "modelo", "accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc",
    "verdaderos_positivos", "falsos_positivos", "falsos_negativos",
    "verdaderos_negativos",
]
MODELOS_METRICAS = (("Híbrido", "modelo_hibrido"), ("Solo reglas", "solo_reglas"))
COLUMNAS_UMBRALES = ["umbral", "precision", "recall", "f1_score", "marcados"]
COLUMNAS_ERRORES = COLUMNAS_RESULTADOS + ["tipo_error"]


def referencia_del_lote(datos: pd.DataFrame) -> pd.Series:
    """Valor 0/1 contra el que se mide el modelo (columna ``es_fraccionamiento``).

    Es la etiqueta del archivo cargado. Si el lote no la trae, se usan los
    dictámenes registrados por un auditor, como en Inteligencia ejecutiva; las
    propuestas y las clasificaciones automáticas no cuentan, porque medir el
    modelo contra sí mismo daría métricas perfectas sin valor.
    """
    sin_valor = pd.Series(pd.NA, index=datos.index)
    etiqueta = pd.to_numeric(
        datos.get("etiqueta_referencia", sin_valor), errors="coerce"
    ).astype("Int64")
    if etiqueta.isin([0, 1]).any():
        return etiqueta
    con_auditor = datos.get("id_usuario_auditor", sin_valor).notna()
    estado = datos.get("estado_revision", sin_valor)
    dictamen = pd.Series(pd.NA, index=datos.index, dtype="Int64")
    dictamen[con_auditor & (estado == "Confirmado_Fraccionamiento")] = 1
    dictamen[con_auditor & (estado == "Descartado")] = 0
    return dictamen


def preparar_resultados(datos: pd.DataFrame) -> pd.DataFrame:
    """Da a las filas del lote las columnas de la hoja "Resultados"."""
    tabla = datos.copy()
    # MySQL entrega las columnas DECIMAL como ``Decimal``.
    for columna in (
        "monto_referencial", "puntaje_riesgo", "score_reglas_negocio", "bono_ia",
        "frecuencia_compras_30d", "monto_acumulado_30d",
    ):
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce")
    tabla["es_fraccionamiento"] = referencia_del_lote(tabla)
    tabla["fecha_convocatoria"] = tabla["fecha_convocatoria"].astype(str)
    # Mismo orden que el archivo de origen, como en el ejemplo.
    if "id_convocatoria" in tabla.columns:
        tabla = tabla.sort_values("id_convocatoria")
    return tabla[COLUMNAS_RESULTADOS].reset_index(drop=True)


def construir_excel_resultados(datos: pd.DataFrame) -> bytes:
    """Libro con las hojas Resultados, Metricas, Umbrales y Errores.

    Las métricas se calculan contra :func:`referencia_del_lote`. Sin etiqueta
    ni dictámenes las tres hojas de evaluación conservan sus cabeceras pero
    quedan vacías: no se inventan resultados que no se pueden medir.
    """
    resultados = preparar_resultados(datos)
    if resultados["es_fraccionamiento"].isin([0, 1]).any():
        metricas, umbrales, errores = _evaluar(resultados)
    else:
        metricas = pd.DataFrame(columns=COLUMNAS_METRICAS)
        umbrales = pd.DataFrame(columns=COLUMNAS_UMBRALES)
        errores = pd.DataFrame(columns=COLUMNAS_ERRORES)

    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        resultados.to_excel(escritor, sheet_name="Resultados", index=False)
        metricas.to_excel(escritor, sheet_name="Metricas", index=False)
        umbrales.to_excel(escritor, sheet_name="Umbrales", index=False)
        errores.to_excel(escritor, sheet_name="Errores", index=False)
    return salida.getvalue()


def _evaluar(resultados: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Metricas, Umbrales y Errores, calculados con las funciones del script."""
    evaluables = resultados.astype({"es_fraccionamiento": "float"})
    informe = evaluar_contra_etiquetas(evaluables, umbral=UMBRAL_ALTO)
    metricas = pd.DataFrame(
        [
            {"modelo": nombre, **informe[clave]}
            for nombre, clave in MODELOS_METRICAS
            if clave in informe
        ]
    )[COLUMNAS_METRICAS]
    umbrales = barrido_de_umbrales(evaluables)[COLUMNAS_UMBRALES]

    etiqueta = evaluables["es_fraccionamiento"]
    prediccion = (evaluables["puntaje_riesgo"] >= UMBRAL_ALTO).astype(int)
    errores = resultados[etiqueta.isin([0, 1]) & (prediccion != etiqueta)].copy()
    errores["tipo_error"] = [
        "Falso positivo" if p == 1 else "Falso negativo"
        for p in prediccion.loc[errores.index]
    ]
    return metricas, umbrales, errores[COLUMNAS_ERRORES]
