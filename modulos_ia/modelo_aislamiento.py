import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

UMBRAL_ALTO = 71.0
UMBRAL_MEDIO = 41.0
BONO_MAXIMO = 20.0
# Anomalía a partir de la cual el ajuste estadístico alcanza el máximo.
ESCALA_ANOMALIA = 0.15


def procesar_estado_revision(
    df: pd.DataFrame,
    modo_automatico: bool = True,
) -> pd.DataFrame:
    """Asigna el estado inicial según el flujo de revisión configurado.

    Un puntaje alto es una señal de riesgo, no una confirmación jurídica: el
    modo automático solo PROPONE un resultado. 'Confirmado_Fraccionamiento' y
    'Descartado' los fija únicamente el dictamen de un auditor.
    """
    df_out = df.copy()
    if modo_automatico:
        condiciones = [
            (df_out['puntaje_riesgo'] >= UMBRAL_ALTO),
            (df_out['puntaje_riesgo'] < UMBRAL_MEDIO),
        ]
        estados = ['Propuesta_Confirmado', 'Propuesta_Descartado']
        df_out['estado_revision'] = np.select(condiciones, estados, default='Pendiente')
    else:
        if 'estado_revision' not in df_out.columns:
            df_out['estado_revision'] = 'Pendiente'
    return df_out


def _matriz_variables(df: pd.DataFrame, mask: pd.Series) -> np.ndarray:
    """Variables independientes del puntaje reglado (evita circularidad)."""
    sub = df.loc[mask]
    if 'ratio_monto_8uit' in sub.columns:
        ratio = sub['ratio_monto_8uit'].astype(float)
    else:
        ratio = sub['monto_acumulado_30d'].astype(float) / (8.0 * 5150.0)
    dias = sub['dias_desde_compra_anterior'].astype(float).clip(upper=365.0)
    return np.column_stack([
        sub['frecuencia_compras_30d'].astype(float),
        sub['max_similitud_nlp'].astype(float),
        np.log1p(ratio.clip(lower=0.0)),
        dias,
    ])


def ejecutar_modelo_aislamiento_hibrido(
    df_procesado: pd.DataFrame,
    contaminacion: float = 0.03,
    modo_automatico: bool = True,
    random_state: int = 42,
) -> pd.DataFrame:
    """Suma al puntaje reglado un ajuste (0 a 20) solo a operaciones atípicas."""
    df = df_procesado.copy()

    if 'es_excluido_normativa' not in df.columns:
        df['es_excluido_normativa'] = False
    if 'max_similitud_nlp' not in df.columns:
        df['max_similitud_nlp'] = df.get('similitud_nlp', 0.0)
    if 'score_reglas_negocio' not in df.columns:
        df['score_reglas_negocio'] = 0.0

    mask_eval = ~df['es_excluido_normativa'].astype(bool)
    df['bono_ia'] = 0.0

    if mask_eval.sum() >= 3:
        X = StandardScaler().fit_transform(_matriz_variables(df, mask_eval))
        iso = IsolationForest(
            n_estimators=100,
            contamination=contaminacion,
            random_state=random_state,
        ).fit(X)
        # decision_function < 0 marca a las operaciones atípicas; las normales
        # (>= 0) no reciben ajuste.
        atipicidad = np.clip(-iso.decision_function(X) / ESCALA_ANOMALIA, 0.0, 1.0)
        df.loc[mask_eval, 'bono_ia'] = np.round(atipicidad * BONO_MAXIMO, 2)

    df['puntaje_riesgo'] = np.clip(df['score_reglas_negocio'] + df['bono_ia'], 0.0, 100.0)

    conds = [
        (df['puntaje_riesgo'] >= UMBRAL_ALTO),
        (df['puntaje_riesgo'] >= UMBRAL_MEDIO) & (df['puntaje_riesgo'] < UMBRAL_ALTO),
        (df['puntaje_riesgo'] < UMBRAL_MEDIO),
    ]
    df['nivel_riesgo'] = np.select(conds, ['Alto', 'Medio', 'Bajo'], default='Bajo')
    df['es_anomalia'] = (df['puntaje_riesgo'] >= UMBRAL_ALTO).astype(int)

    return procesar_estado_revision(df, modo_automatico=modo_automatico)


def entrenar_y_evaluar_isolation_forest(
    df_caracteristicas: pd.DataFrame,
    contaminacion: float = 0.03,
    random_state: int = 42,
    modo_automatico: bool = True,
):
    """Mantiene la firma utilizada por la capa de ingesta."""
    df_res = ejecutar_modelo_aislamiento_hibrido(
        df_caracteristicas,
        contaminacion=contaminacion,
        modo_automatico=modo_automatico,
        random_state=random_state,
    )
    return df_res, None, None
