"""Modelo supervisado que aprende de etiquetas y dictámenes acumulados.

Permanece inactivo mientras no supere al puntaje actual (reglas + ajuste
estadístico) en una validación agrupada por entidad: el modelo nunca se evalúa
con entidades que vio al entrenar, como ocurre con un lote nuevo. Aun cuando la
supere, su activación la confirma una persona. Inactivo, no altera ningún
puntaje.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.utils.class_weight import compute_sample_weight

from modulos_ia.extractor_caracteristicas import PALABRAS_CLAVE_AUDITORIA, _texto_basico
from modulos_ia.modelo_aislamiento import UMBRAL_ALTO, UMBRAL_MEDIO

# Datos mínimos para que la validación por entidades sea creíble.
MIN_CASOS_POSITIVOS = 50
MIN_CASOS_NEGATIVOS = 50
MIN_ENTIDADES_NEGATIVAS = 10
# Mejora mínima en exactitud balanceada sobre el puntaje actual.
MARGEN_EXACTITUD_BALANCEADA = 0.05
# Probabilidad que equivale al umbral de alerta (los pesos de clase la centran).
UMBRAL_PROBABILIDAD = 0.5
MAX_PLIEGUES = 5
# Test de permutación: con 49 barajados, p ≤ 0,02 exige superar a todos.
PERMUTACIONES = 49
VALOR_P_MAXIMO = 0.02

# Variables guardadas en resultados_anomalias y disponibles en la ingesta.
VARIABLES = [
    "frecuencia_compras_30d",
    "similitud_nlp",
    "monto_acumulado_30d",
    "monto_referencial",
    "dias_desde_compra_anterior",
    "score_reglas_negocio",
]
NOMBRE_MODELO = "Aprendizaje supervisado"


def matriz_variables(datos: pd.DataFrame) -> np.ndarray:
    """Variables del modelo; los montos en escala logarítmica."""
    tabla = datos[VARIABLES].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return np.column_stack([
        tabla["frecuencia_compras_30d"],
        tabla["similitud_nlp"],
        np.log1p(tabla["monto_acumulado_30d"].clip(lower=0)),
        np.log1p(tabla["monto_referencial"].clip(lower=0)),
        tabla["dias_desde_compra_anterior"].clip(upper=365),
        tabla["score_reglas_negocio"],
    ]).astype(float)


def puntaje_actual(datos: pd.DataFrame) -> np.ndarray:
    """Puntaje de reglas + ajuste estadístico, independiente del modelo supervisado."""
    reglas = pd.to_numeric(datos["score_reglas_negocio"], errors="coerce").fillna(0.0)
    bono = pd.to_numeric(datos["bono_ia"], errors="coerce").fillna(0.0)
    return np.clip(reglas + bono, 0.0, 100.0).to_numpy(float)


def casos_de_referencia(filas: pd.DataFrame) -> pd.DataFrame:
    """Casos con referencia 0/1, sin duplicados entre lotes.

    La referencia es el dictamen de un auditor o, si no lo hay, la etiqueta del
    archivo cargado. Las propuestas y clasificaciones automáticas no cuentan:
    aprender de ellas sería aprender del propio sistema. Una misma compra
    cargada en varios lotes se cuenta una sola vez (prevalece la que tenga
    dictamen y, si no, la más reciente), para no inflar la validación.
    """
    datos = filas.copy()
    # Los lotes cargados antes de excluir los resúmenes de hallazgo los guardaron
    # como compras, a veces con el CUBSO numérico. Para entrenar basta la palabra
    # de auditoría en el texto: descartar alguna compra real cuesta poco, y un
    # resumen enseñaría al modelo a leer la respuesta en la descripción.
    con_palabra = datos["descripcion_item"].map(_texto_basico).map(
        lambda texto: any(clave in texto for clave in PALABRAS_CLAVE_AUDITORIA)
    )
    datos = datos.loc[~con_palabra]
    con_auditor = datos["id_usuario_auditor"].notna()
    dictamen = pd.Series(np.nan, index=datos.index)
    dictamen[con_auditor & (datos["estado_revision"] == "Confirmado_Fraccionamiento")] = 1
    dictamen[con_auditor & (datos["estado_revision"] == "Descartado")] = 0
    etiqueta = pd.to_numeric(datos["etiqueta_referencia"], errors="coerce")
    datos["referencia"] = dictamen.fillna(etiqueta)
    datos["tiene_dictamen"] = dictamen.notna()
    datos = datos[datos["referencia"].isin([0, 1])]

    clave = ["entidad_ruc", "descripcion_item", "monto_referencial", "fecha_convocatoria"]
    datos = datos.assign(
        monto_referencial=pd.to_numeric(datos["monto_referencial"], errors="coerce").round(2),
        fecha_convocatoria=datos["fecha_convocatoria"].astype(str),
    )
    datos = datos.sort_values(["tiene_dictamen", "id_resultado"]).drop_duplicates(clave, keep="last")
    datos["referencia"] = datos["referencia"].astype(int)
    return datos.reset_index(drop=True)


@dataclass
class Validacion:
    positivos: int
    negativos: int
    entidades: int
    entidades_negativas: int
    suficiente: bool
    supera: bool = False
    motivo: str = ""
    modelo: dict = field(default_factory=dict)
    actual: dict = field(default_factory=dict)


def _metricas(y: np.ndarray, decision: np.ndarray, puntaje: np.ndarray) -> dict:
    return {
        "exactitud_balanceada": float(balanced_accuracy_score(y, decision)),
        "roc_auc": float(roc_auc_score(y, puntaje)),
        "sensibilidad": float(decision[y == 1].mean()),
        "especificidad": float(1 - decision[y == 0].mean()),
    }


def _nuevo_modelo() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(
        n_estimators=150, max_depth=2, learning_rate=0.05, random_state=42
    )


def validar(casos: pd.DataFrame) -> Validacion:
    """Compara el modelo con el puntaje actual en entidades no vistas."""
    y = casos["referencia"].to_numpy(int) if len(casos) else np.array([], dtype=int)
    grupos = casos["entidad_ruc"].astype(str).to_numpy() if len(casos) else np.array([])
    resultado = Validacion(
        positivos=int(y.sum()),
        negativos=int((y == 0).sum()),
        entidades=len(set(grupos)),
        entidades_negativas=len(set(grupos[y == 0])),
        suficiente=False,
    )
    faltan = []
    if resultado.positivos < MIN_CASOS_POSITIVOS:
        faltan.append(f"{MIN_CASOS_POSITIVOS} casos con fraccionamiento")
    if resultado.negativos < MIN_CASOS_NEGATIVOS:
        faltan.append(f"{MIN_CASOS_NEGATIVOS} casos conformes")
    if resultado.entidades_negativas < MIN_ENTIDADES_NEGATIVAS:
        faltan.append(f"casos conformes de {MIN_ENTIDADES_NEGATIVAS} entidades")
    resultado.suficiente = not faltan
    if len(set(y)) < 2 or resultado.entidades < 2:
        resultado.motivo = "Faltan " + ", ".join(faltan) + "." if faltan else "Se necesitan casos de ambas clases."
        return resultado

    X = matriz_variables(casos)
    probabilidad = _probabilidad_fuera_de_muestra(X, y, grupos)

    actual = puntaje_actual(casos)
    decision_modelo = (probabilidad >= UMBRAL_PROBABILIDAD).astype(int)
    decision_actual = (actual >= UMBRAL_ALTO).astype(int)
    resultado.modelo = _metricas(y, decision_modelo, probabilidad)
    resultado.actual = _metricas(y, decision_actual, actual)
    piso_modelo, piso_mejora = _limites_bootstrap(y, decision_modelo, decision_actual, grupos)
    resultado.modelo["exactitud_balanceada_piso_95"] = piso_modelo
    resultado.modelo["mejora_piso_95"] = piso_mejora
    mejora = resultado.modelo["exactitud_balanceada"] - resultado.actual["exactitud_balanceada"]
    # Ganar en una sola partición puede ser suerte: además del margen, la
    # ventaja debe mantenerse al remuestrear entidades y el modelo debe superar
    # lo que logra el mismo procedimiento con etiquetas barajadas.
    supera_metricas = (
        mejora >= MARGEN_EXACTITUD_BALANCEADA
        and resultado.modelo["roc_auc"] >= resultado.actual["roc_auc"]
        and piso_modelo > 0.5
        and piso_mejora > 0.0
    )
    if supera_metricas:
        valor_p = _valor_p_permutacion(X, y, grupos, resultado.modelo["exactitud_balanceada"])
        resultado.modelo["valor_p_permutacion"] = valor_p
        supera_metricas = valor_p <= VALOR_P_MAXIMO
    resultado.supera = resultado.suficiente and supera_metricas
    if not resultado.suficiente:
        resultado.motivo = "Faltan " + ", ".join(faltan) + ": la validación es solo orientativa."
    elif not supera_metricas:
        resultado.motivo = (
            f"No supera al puntaje actual de forma fiable: se exige un {MARGEN_EXACTITUD_BALANCEADA:.0%} "
            "más de exactitud balanceada, sin empeorar el ROC-AUC, que la ventaja se "
            "mantenga al remuestrear entidades (95 % de confianza) y que supere a todos "
            "los entrenamientos con etiquetas barajadas."
        )
    return resultado


def _probabilidad_fuera_de_muestra(X: np.ndarray, y: np.ndarray, grupos: np.ndarray) -> np.ndarray:
    """Probabilidad de cada caso con un modelo que no vio su entidad."""
    probabilidad = np.zeros(len(y))
    pliegues = GroupKFold(n_splits=min(MAX_PLIEGUES, len(set(grupos))))
    for entrenamiento, prueba in pliegues.split(X, y, grupos):
        if len(set(y[entrenamiento])) < 2:
            probabilidad[prueba] = y[entrenamiento].mean()
            continue
        modelo = _nuevo_modelo().fit(
            X[entrenamiento], y[entrenamiento],
            sample_weight=compute_sample_weight("balanced", y[entrenamiento]),
        )
        probabilidad[prueba] = modelo.predict_proba(X[prueba])[:, 1]
    return probabilidad


def _valor_p_permutacion(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, observado: float) -> float:
    """Proporción de barajados de etiquetas que igualan o superan al modelo real."""
    rng = np.random.default_rng(42)
    iguales_o_mejores = 0
    for _ in range(PERMUTACIONES):
        barajadas = rng.permutation(y)
        decision = _probabilidad_fuera_de_muestra(X, barajadas, grupos) >= UMBRAL_PROBABILIDAD
        if balanced_accuracy_score(barajadas, decision) >= observado:
            iguales_o_mejores += 1
    return (iguales_o_mejores + 1) / (PERMUTACIONES + 1)


def _limites_bootstrap(
    y: np.ndarray,
    decision_modelo: np.ndarray,
    decision_actual: np.ndarray,
    grupos: np.ndarray,
    repeticiones: int = 1000,
) -> tuple[float, float]:
    """Percentil 5 de la exactitud balanceada del modelo y de su mejora.

    Se remuestrean entidades completas, no filas: las compras de una misma
    entidad no son independientes entre sí.
    """
    rng = np.random.default_rng(42)
    entidades = np.unique(grupos)
    filas_por_entidad = {e: np.flatnonzero(grupos == e) for e in entidades}
    modelo, mejora = [], []
    for _ in range(repeticiones):
        filas = np.concatenate([filas_por_entidad[e] for e in rng.choice(entidades, len(entidades))])
        if len(set(y[filas])) < 2:
            continue
        bal_modelo = balanced_accuracy_score(y[filas], decision_modelo[filas])
        modelo.append(bal_modelo)
        mejora.append(bal_modelo - balanced_accuracy_score(y[filas], decision_actual[filas]))
    if not modelo:
        return 0.0, -1.0
    return float(np.percentile(modelo, 5)), float(np.percentile(mejora, 5))


def entrenar(casos: pd.DataFrame) -> GradientBoostingClassifier:
    """Entrena con todos los casos de referencia (tras una validación superada)."""
    y = casos["referencia"].to_numpy(int)
    return _nuevo_modelo().fit(
        matriz_variables(casos), y, sample_weight=compute_sample_weight("balanced", y)
    )


def probabilidad_a_puntaje(probabilidad: np.ndarray) -> np.ndarray:
    """Escala 0-100 en la que la probabilidad de corte cae justo en 71 puntos.

    Así las reglas de la aplicación (nivel Alto desde 71, propuestas) siguen
    significando lo mismo con el modelo activo.
    """
    p = np.clip(np.asarray(probabilidad, dtype=float), 0.0, 1.0)
    t = UMBRAL_PROBABILIDAD
    return np.round(
        np.where(p < t, UMBRAL_ALTO * p / t, UMBRAL_ALTO + (100 - UMBRAL_ALTO) * (p - t) / (1 - t)), 2
    )


def aplicar(resultados: pd.DataFrame, modelo) -> pd.DataFrame:
    """Puntúa con el modelo activo; sin modelo devuelve los resultados intactos."""
    if modelo is None or resultados.empty:
        return resultados
    salida = resultados.copy()
    probabilidad = modelo.predict_proba(matriz_variables(salida))[:, 1]
    salida["puntaje_riesgo"] = probabilidad_a_puntaje(probabilidad)
    salida["nivel_riesgo"] = np.select(
        [salida["puntaje_riesgo"] >= UMBRAL_ALTO, salida["puntaje_riesgo"] >= UMBRAL_MEDIO],
        ["Alto", "Medio"],
        default="Bajo",
    )
    salida["es_anomalia"] = (salida["puntaje_riesgo"] >= UMBRAL_ALTO).astype(int)
    salida["explicacion_reglas"] = [
        f"{texto}; {NOMBRE_MODELO}: probabilidad {p:.0%} (reglas + ajuste: {a:.1f} pts)"
        for texto, p, a in zip(salida["explicacion_reglas"].astype(str), probabilidad, puntaje_actual(salida))
    ]
    return salida
