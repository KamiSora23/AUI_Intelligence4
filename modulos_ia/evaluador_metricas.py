import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

UMBRAL_ALTO = 71.0


def _metricas(y_true, y_pred, y_scores) -> dict:
    """Métricas de clasificación.

    Con clases desbalanceadas, precisión y F1 engañan: marcar todo como
    fraccionamiento da F1 alto si casi todo lo es. Por eso se incluyen
    especificidad, exactitud balanceada y MCC.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    resultado = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "especificidad": round(float(tn / (tn + fp)), 4) if (tn + fp) else None,
        "exactitud_balanceada": (
            round(float(balanced_accuracy_score(y_true, y_pred)), 4)
            if len(np.unique(y_true)) > 1 else None
        ),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "mcc": round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "roc_auc": None,
        "pr_auc": None,
        "verdaderos_positivos": int(tp),
        "falsos_positivos": int(fp),
        "falsos_negativos": int(fn),
        "verdaderos_negativos": int(tn),
    }
    # Con una sola clase el AUC no está definido: se informa como None en lugar
    # de inventar un valor de referencia.
    if len(np.unique(y_true)) > 1:
        resultado["roc_auc"] = round(float(roc_auc_score(y_true, y_scores)), 4)
        resultado["pr_auc"] = round(float(average_precision_score(y_true, y_scores)), 4)
    return resultado


def metricas_de_referencia(y_true) -> dict:
    """Desempeño de marcar todo como fraccionamiento: el piso que hay que superar."""
    y_true = np.asarray(y_true).astype(int)
    return _metricas(y_true, np.ones_like(y_true), np.ones(len(y_true)))


def evaluar_performance_sobre_feedback(df_resultados_validados: pd.DataFrame, solo_auditor: bool = True):
    """
    Métricas sobre los registros con dictamen del Auditor (Human-in-the-Loop):
    - 'Confirmado_Fraccionamiento' -> positivo (1)
    - 'Descartado' -> negativo (0)

    Con ``solo_auditor=True`` y la columna ``id_usuario_auditor`` presente, solo
    cuentan los dictámenes humanos. Los estados asignados por el flujo
    automático los fija el propio modelo y evaluarlos contra sí mismo es
    circular.
    """
    df = df_resultados_validados.copy()
    df_val = df[df['estado_revision'].isin(['Confirmado_Fraccionamiento', 'Descartado'])].copy()
    if solo_auditor and 'id_usuario_auditor' in df_val.columns:
        df_val = df_val[df_val['id_usuario_auditor'].notna()]

    if df_val.empty:
        return {
            "total_validados": 0,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "roc_auc": None,
            "mensaje": "No hay casos dictaminados por un auditor para calcular métricas.",
        }

    y_true = (df_val['estado_revision'] == 'Confirmado_Fraccionamiento').astype(int).values
    resultado = _metricas(y_true, df_val['es_anomalia'].values, df_val['puntaje_riesgo'].values)
    resultado["total_validados"] = len(df_val)
    resultado["mensaje"] = "Métricas calculadas sobre dictámenes de auditoría (Human-in-the-Loop)."
    return resultado


def evaluar_contra_etiquetas(
    df_resultados: pd.DataFrame,
    columna_etiqueta: str = 'es_fraccionamiento',
    columna_puntaje: str = 'puntaje_riesgo',
    umbral: float = UMBRAL_ALTO,
) -> dict:
    """Mide el modelo contra una etiqueta de referencia (0 = conforme, 1 = fraccionamiento).

    Las filas sin etiqueta (por ejemplo, filas de contexto) se ignoran. Devuelve
    las métricas del puntaje consolidado y las del puntaje de reglas solas, para
    ver cuánto aporta el ajuste estadístico.
    """
    etiqueta = pd.to_numeric(df_resultados[columna_etiqueta], errors='coerce')
    mascara = etiqueta.isin([0, 1])
    if not mascara.any():
        raise ValueError(f"La columna '{columna_etiqueta}' no contiene etiquetas 0/1.")

    y_true = etiqueta[mascara].astype(int).to_numpy()
    puntaje = df_resultados.loc[mascara, columna_puntaje].astype(float).to_numpy()
    resultado = {
        "total_evaluados": int(mascara.sum()),
        "positivos": int(y_true.sum()),
        "negativos": int((1 - y_true).sum()),
        "umbral": float(umbral),
        "referencia_todo_positivo": metricas_de_referencia(y_true),
        "modelo_hibrido": _metricas(y_true, puntaje >= umbral, puntaje),
    }
    if 'score_reglas_negocio' in df_resultados.columns:
        reglas = df_resultados.loc[mascara, 'score_reglas_negocio'].astype(float).to_numpy()
        resultado["solo_reglas"] = _metricas(y_true, reglas >= min(umbral, 80.0), reglas)
    return resultado


def barrido_de_umbrales(
    df_resultados: pd.DataFrame,
    columna_etiqueta: str = 'es_fraccionamiento',
    columna_puntaje: str = 'puntaje_riesgo',
    umbrales=range(10, 95, 5),
) -> pd.DataFrame:
    """Métricas para varios umbrales; sirve para calibrar el corte."""
    etiqueta = pd.to_numeric(df_resultados[columna_etiqueta], errors='coerce')
    mascara = etiqueta.isin([0, 1])
    y_true = etiqueta[mascara].astype(int).to_numpy()
    puntaje = df_resultados.loc[mascara, columna_puntaje].astype(float).to_numpy()
    filas = []
    for u in umbrales:
        pred = (puntaje >= u).astype(int)
        m = _metricas(y_true, pred, puntaje)
        filas.append({
            "umbral": u,
            "precision": m["precision"],
            "recall": m["recall"],
            "especificidad": m["especificidad"],
            "exactitud_balanceada": m["exactitud_balanceada"],
            "f1_score": m["f1_score"],
            "marcados": int(pred.sum()),
        })
    return pd.DataFrame(filas)
