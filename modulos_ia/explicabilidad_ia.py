import numpy as np
import pandas as pd

from utilidades.estados_revision import texto_separacion

def nombres_variables(ventana: str = "la ventana") -> dict[str, str]:
    """Nombres legibles de las variables; ``ventana`` es p. ej. '45 días'."""
    return {
        'similitud_nlp': 'Similitud temática',
        'monto_acumulado_30d': f'Monto acumulado en {ventana} (PEN)',
        'frecuencia_compras_30d': f'Frecuencia de compras en {ventana}',
        'dias_desde_compra_anterior': 'Proximidad Temporal (Días Previos)'
    }


def calcular_explicabilidad_caso(row_data: dict, scaler=None, model=None, ventana: str = "la ventana"):
    """
    Calcula la contribución de impacto porcentual de cada variable (XAI)
    sobre el score de riesgo del caso seleccionado.
    Retorna un DataFrame ordenado con la variable, valor real, impacto % y dirección.
    """
    nombres = nombres_variables(ventana)
    if model is not None and scaler is not None:
        try:
            import shap
            raw_vals = np.array([[
                row_data.get('similitud_nlp', 0.0),
                row_data.get('monto_acumulado_30d', 0.0),
                row_data.get('frecuencia_compras_30d', 0),
                row_data.get('dias_desde_compra_anterior', 0)
            ]])
            scaled_vals = scaler.transform(raw_vals)
            
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(scaled_vals)
            
            if isinstance(shap_values, list):
                shap_vals_row = np.abs(shap_values[0][0])
            else:
                shap_vals_row = np.abs(shap_values[0])

            total_shap = np.sum(shap_vals_row) if np.sum(shap_vals_row) > 0 else 1.0
            impacto_pct = (shap_vals_row / total_shap) * 100.0
        except Exception:
            impacto_pct = _calcular_impacto_proporcional(row_data)
    else:
        impacto_pct = _calcular_impacto_proporcional(row_data)

    # Construir DataFrame de explicación
    df_explicacion = pd.DataFrame({
        'variable_codigo': list(nombres.keys()),
        'variable_nombre': list(nombres.values()),
        'valor_observado': [
            f"{float(row_data.get('similitud_nlp', 0.0)):.2%}",
            f"S/ {float(row_data.get('monto_acumulado_30d', 0.0)):,.2f}",
            f"{int(row_data.get('frecuencia_compras_30d', 0))} compras",
            texto_separacion(row_data.get('dias_desde_compra_anterior')),
        ],
        'impacto_porcentaje': np.round(impacto_pct, 2)
    }).sort_values(by='impacto_porcentaje', ascending=False).reset_index(drop=True)

    return df_explicacion


def _calcular_impacto_proporcional(row_data: dict) -> np.ndarray:
    """Calcula la aproximación existente sin cargar la biblioteca SHAP."""
        # Estimación proporcional cuando no existe un explicador persistido.
    nlp_val = float(row_data.get('similitud_nlp', 0.0))
    monto_val = float(row_data.get('monto_acumulado_30d', 0.0))
    freq_val = float(row_data.get('frecuencia_compras_30d', 0))
    dias_val = float(row_data.get('dias_desde_compra_anterior', 30))

    # Ponderación basada en la heurística del modelo de anomalía
    comp_nlp = nlp_val * 4.0
    comp_monto = min(monto_val / 50000.0, 3.0)
    comp_freq = min(freq_val / 3.0, 3.0)
    comp_dias = max(0, (30.0 - min(dias_val, 30.0)) / 10.0)

    raw_scores = np.array([comp_nlp, comp_monto, comp_freq, comp_dias])
    total = np.sum(raw_scores) if np.sum(raw_scores) > 0 else 1.0
    return (raw_scores / total) * 100.0
