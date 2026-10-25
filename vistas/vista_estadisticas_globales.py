import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import text
from base_datos.conexion_bd import obtener_engine, obtener_session
from utilidades.gestor_lotes import renderizar_selector_lote_global
from vistas.componentes_ui import (
    encabezado_pagina,
    encabezado_seccion,
    estilizar_grafica,
    tarjeta_metrica,
)


@st.cache_data(ttl=30, show_spinner=False)
def _cargar_datos_estadisticos(lote_id: int) -> pd.DataFrame:
    """Recupera una instantánea reutilizable para los indicadores ejecutivos."""
    session = obtener_session()
    try:
        filas = session.execute(
            text(
                """
                SELECT
                    r.id_resultado,
                    c.entidad_ruc,
                    c.entidad_nombre,
                    c.monto_referencial,
                    c.fecha_convocatoria,
                    r.puntaje_riesgo,
                    r.score_reglas_negocio,
                    r.es_anomalia,
                    r.estado_revision,
                    r.id_usuario_auditor,
                    r.etiqueta_referencia
                FROM resultados_anomalias r
                JOIN convocatorias_procesadas c
                    ON r.id_convocatoria = c.id_convocatoria
                WHERE c.id_carga = :lote
                """
            ),
            {"lote": lote_id},
        ).fetchall()
        return (
            pd.DataFrame([dict(fila._mapping) for fila in filas])
            if filas
            else pd.DataFrame()
        )
    finally:
        session.close()


@st.cache_data(ttl=30, show_spinner=False)
def _cargar_umbral_alerta_pts() -> float:
    """Obtiene de MySQL el corte vigente y lo expresa en puntos sobre 100."""
    session = obtener_session()
    try:
        fila = session.execute(
            text(
                """
                SELECT umbral_alerta_notificacion
                FROM configuracion_sistema
                ORDER BY id_config DESC
                LIMIT 1
                """
            )
        ).fetchone()
        umbral = (
            float(fila[0])
            if fila and fila[0] is not None
            else 0.80
        )
        return umbral * 100.0 if umbral <= 1.0 else umbral
    finally:
        session.close()


def renderizar_vista_estadisticas():
    """Consolida métricas del modelo y tendencias de contratación."""
    encabezado_pagina(
        "Inteligencia ejecutiva",
        "Indicadores de desempeño, concentración de riesgo y evolución de las contrataciones.",
        "chart",
        "Analítica consolidada",
    )

    lote_id = renderizar_selector_lote_global(
        obtener_engine(),
        clave_componente="sel_inteligencia_global",
    )
    if lote_id is None:
        return

    try:
        df_data = _cargar_datos_estadisticos(lote_id).copy()
        if not df_data.empty:
            df_data['monto_referencial'] = pd.to_numeric(df_data['monto_referencial'], errors='coerce').fillna(0.0)
            df_data['puntaje_riesgo'] = pd.to_numeric(df_data['puntaje_riesgo'], errors='coerce').fillna(0.0)
            df_data['score_reglas_negocio'] = pd.to_numeric(
                df_data['score_reglas_negocio'], errors='coerce'
            ).fillna(0.0)
            df_data['es_anomalia'] = pd.to_numeric(df_data['es_anomalia'], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        st.error(f"Error al recuperar datos estadísticos: {e}")
        return

    if df_data.empty:
        st.info("No hay datos procesados para construir indicadores.")
        return

    # Las métricas solo son representativas sobre casos revisados.
    encabezado_seccion(
        "Desempeño del modelo",
        "Comparación del baseline de reglas normativas frente al dictamen del modelo híbrido.",
        "brain",
    )

    # Si el archivo cargado trae una etiqueta de referencia (p. ej. casos
    # confirmados por la Contraloría), las métricas se calculan contra ella: es
    # una verdad externa al modelo. Si no, solo cuentan los dictámenes de un
    # auditor; en el flujo automático el estado lo fija el propio modelo y
    # medirlo contra sí mismo produciría métricas perfectas sin valor.
    tiene_etiquetas = (
        "etiqueta_referencia" in df_data.columns
        and pd.to_numeric(df_data["etiqueta_referencia"], errors="coerce")
        .isin([0, 1])
        .any()
    )
    if tiene_etiquetas:
        df_data["etiqueta_referencia"] = pd.to_numeric(
            df_data["etiqueta_referencia"], errors="coerce"
        )
        df_validos = df_data[df_data["etiqueta_referencia"].isin([0, 1])].copy()
    else:
        df_validos = df_data[
            df_data["estado_revision"].isin(
                ["Confirmado_Fraccionamiento", "Descartado"]
            )
            & df_data["id_usuario_auditor"].notna()
        ].copy()

    if not df_validos.empty:
        if tiene_etiquetas:
            y_real = df_validos["etiqueta_referencia"].astype(int)
        else:
            y_real = (
                df_validos["estado_revision"] == "Confirmado_Fraccionamiento"
            ).astype(int)
        umbral_global_pts = _cargar_umbral_alerta_pts()
        umbral_reglas_eval = min(umbral_global_pts, 80.0)
        # Baseline: decisión que habrían tomado únicamente las reglas
        # normativas. Su escala tiene un tope propio de 80 puntos.
        if tiene_etiquetas:
            # Se mide el modelo híbrido completo contra la etiqueta de referencia.
            y_pred = (df_validos["puntaje_riesgo"] >= 71.0).astype(int)
        else:
            y_pred = (
                df_validos["score_reglas_negocio"] >= umbral_reglas_eval
            ).astype(int)
        y_prob = (df_validos["puntaje_riesgo"] / 100.0).clip(0.0, 1.0)

        acc = accuracy_score(y_real, y_pred)
        prec = precision_score(y_real, y_pred, zero_division=0)
        rec = recall_score(y_real, y_pred, zero_division=0)
        f1 = f1_score(y_real, y_pred, zero_division=0)

        auc_val = None
        if len(np.unique(y_real)) > 1:
            try:
                auc_val = float(roc_auc_score(y_real, y_prob))
                if np.isnan(auc_val):
                    auc_val = None
            except Exception:
                auc_val = None

        col_m0, col_m1, col_m2, col_m3, col_m4 = st.columns(5)
        with col_m0:
            tarjeta_metrica(
                "Accuracy", f"{acc * 100:.1f}%",
                "Clasificaciones correctas", "activity",
            )
        with col_m1:
            tarjeta_metrica(
                "Precisión", f"{prec * 100:.1f}%",
                "Predicciones positivas correctas", "shield",
            )
        with col_m2:
            tarjeta_metrica(
                "Sensibilidad", f"{rec * 100:.1f}%",
                "Casos relevantes identificados", "activity", "success",
            )
        with col_m3:
            tarjeta_metrica(
                "Valor F1", f"{f1 * 100:.1f}%",
                "Balance del desempeño", "brain", "warning",
            )
        with col_m4:
            tarjeta_metrica(
                "Área ROC",
                f"{auc_val:.3f}" if auc_val is not None else "N/D",
                (
                    "Capacidad de discriminación"
                    if auc_val is not None
                    else "Requiere casos de ambas clases"
                ),
                "chart", "danger",
            )

        # Con clases desbalanceadas, accuracy, precisión y F1 se inflan: marcar
        # todo como fraccionamiento ya las haría altas. Estas tres muestran si el
        # modelo distingue de verdad entre casos con y sin fraccionamiento.
        especificidad = (
            float(((y_pred == 0) & (y_real == 0)).sum() / (y_real == 0).sum())
            if (y_real == 0).any()
            else None
        )
        exactitud_bal = (
            balanced_accuracy_score(y_real, y_pred) if y_real.nunique() > 1 else None
        )
        prevalencia = float(y_real.mean())
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            tarjeta_metrica(
                "Especificidad",
                f"{especificidad * 100:.1f}%" if especificidad is not None else "N/D",
                "Casos sin fraccionamiento descartados correctamente",
                "shield",
            )
        with col_b2:
            tarjeta_metrica(
                "Exactitud balanceada",
                f"{exactitud_bal * 100:.1f}%" if exactitud_bal is not None else "N/D",
                "50% equivale a decidir al azar",
                "activity",
                "success" if exactitud_bal is not None and exactitud_bal >= 0.7 else "warning",
            )
        with col_b3:
            tarjeta_metrica(
                "Referencia: marcar todo",
                f"{prevalencia * 100:.1f}%",
                "Precisión que se obtendría alertando todos los casos",
                "chart",
            )
        if exactitud_bal is not None and exactitud_bal < 0.6:
            st.warning(
                f"Con {prevalencia:.0%} de casos positivos, la precisión y el F1 parecen "
                f"altos aunque el modelo apenas distinga los casos: la exactitud balanceada "
                f"es {exactitud_bal:.1%}. Antes de ajustar umbrales conviene contar con más "
                f"casos conformes de distintas entidades."
            )

        if tiene_etiquetas:
            st.caption(
                f"Métricas calculadas sobre {len(df_validos):,} casos con etiqueta "
                f"de referencia del lote {lote_id}. Predicción: modelo híbrido "
                f"(puntaje ≥ 71 = fraccionamiento)."
            )
        else:
            st.caption(
                f"Métricas calculadas sobre {len(df_validos):,} casos "
                f"dictaminados del lote {lote_id}. Predicción: reglas puras "
                f"(score ≥ {int(umbral_reglas_eval)}); referencia: dictamen "
                f"de auditoría."
            )
    else:
        st.info(
            "No hay expedientes dictaminados por un auditor en el lote "
            "actual para calcular las métricas."
        )

    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        with st.container(border=True):
            encabezado_seccion(
                "Exposición por entidad",
                "Monto acumulado en operaciones con riesgo medio o alto.",
                "activity",
            )

            df_ranking = df_data[df_data['puntaje_riesgo'] >= 41.0].groupby('entidad_nombre')['monto_referencial'].sum().reset_index()
            df_ranking = df_ranking.sort_values(by='monto_referencial', ascending=True).tail(10)

            fig_rank = px.bar(
                df_ranking,
                x="monto_referencial",
                y="entidad_nombre",
                orientation="h",
                labels={
                    "monto_referencial": "Exposición (PEN)",
                    "entidad_nombre": "Entidad pública",
                },
                color="monto_referencial",
                color_continuous_scale=[
                    [0.0, "#8B7CFF"],
                    [0.55, "#F2B84B"],
                    [1.0, "#FF6F87"],
                ],
            )
            fig_rank.update_layout(coloraxis_showscale=False)
            estilizar_grafica(fig_rank, altura=350, mostrar_leyenda=False)
            st.plotly_chart(
                fig_rank,
                width="stretch",
                config={"displaylogo": False, "responsive": True},
            )

    with col_g2:
        with st.container(border=True):
            encabezado_seccion(
                "Evolución temporal",
                "Comportamiento mensual de operaciones normales y anómalas.",
                "chart",
            )

            df_data['mes_anio'] = pd.to_datetime(df_data['fecha_convocatoria']).dt.to_period('M').astype(str)
            df_evo = df_data.groupby(['mes_anio', 'es_anomalia']).size().reset_index(name='conteo')
            df_evo['Tipo'] = df_evo['es_anomalia'].map({1: 'Anomalía detectada', 0: 'Normal'})

            fig_line = px.line(
                df_evo,
                x="mes_anio",
                y="conteo",
                color="Tipo",
                markers=True,
                labels={"mes_anio": "Mes / año", "conteo": "Operaciones"},
                color_discrete_map={
                    "Anomalía detectada": "#FF6F87",
                    "Normal": "#8B7CFF",
                },
            )
            fig_line.update_traces(line={"width": 3}, marker={"size": 7})
            estilizar_grafica(fig_line, altura=350, mostrar_leyenda=True)
            st.plotly_chart(
                fig_line,
                width="stretch",
                config={"displaylogo": False, "responsive": True},
            )
