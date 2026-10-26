import os

import pandas as pd
import streamlit as st
from sqlalchemy import text
from base_datos.conexion_bd import obtener_engine, obtener_session
from base_datos.gestor_logs import registrar_log
from modulos_ia.aprendizaje_supervisado import (
    MIN_CASOS_NEGATIVOS,
    MIN_CASOS_POSITIVOS,
    MIN_ENTIDADES_NEGATIVAS,
    validar,
)
from utilidades.gestor_modelo_supervisado import (
    activar,
    cargar_casos,
    desactivar,
    modelo_activo,
)
from vistas.componentes_ui import encabezado_pagina, encabezado_seccion, tarjeta_metrica

# Opciones de ventana de recurrencia (días → texto mostrado).
VENTANAS_DIAS = {
    15: "15 días",
    30: "30 días",
    45: "45 días",
    60: "60 días",
    90: "90 días (3 meses)",
    180: "180 días (6 meses)",
    270: "270 días (9 meses)",
    365: "365 días (12 meses)",
}


@st.cache_data(ttl=60, show_spinner=False)
def _cargar_configuracion_actual():
    """Mantiene disponible la configuración vigente durante la navegación."""
    session = obtener_session()
    try:
        fila = session.execute(
            text(
                "SELECT * FROM configuracion_sistema "
                "ORDER BY id_config DESC LIMIT 1"
            )
        ).fetchone()
        return dict(fila._mapping) if fila else None
    finally:
        session.close()


def mostrar_vista_configuracion(conexion_bd=None):
    """Conserva el punto de entrada utilizado por integraciones anteriores."""
    renderizar_vista_configuracion()

def renderizar_vista_configuracion():
    """Administra los parámetros que gobiernan el análisis y la revisión."""
    encabezado_pagina(
        "Modelo y parámetros",
        "Administra los umbrales operativos, la ventana de análisis y el flujo de revisión.",
        "settings",
        "Configuración del sistema",
    )

    try:
        config_actual = _cargar_configuracion_actual()
    except Exception as e:
        st.error(f"Error al cargar configuración: {e}")
        config_actual = None

    # La última configuración guardada es la vigente.
    contam_def = float(config_actual.get('frecuencia_contaminacion', 0.030)) if config_actual else 0.030
    nlp_def = float(config_actual.get('umbral_similitud_nlp', 0.50)) if config_actual else 0.50
    ventana_def = int(config_actual.get('ventana_dias', 30)) if config_actual else 30
    uit_def = float(config_actual.get('monto_uit_vigente', 5150.00)) if config_actual else 5150.00
    alerta_def = float(config_actual.get('umbral_alerta_notificacion', 0.85)) if config_actual else 0.85
    flujo_def = config_actual.get('flujo_revision', 'Automático') if config_actual else 'Automático'

    encabezado_seccion(
        "Parámetros del modelo",
        "Ajustes utilizados durante el procesamiento de nuevas fuentes.",
        "brain",
    )

    col1, col2 = st.columns(2)

    with col1:
        contaminacion = st.slider(
            "Proporción esperada de casos atípicos",
            min_value=0.01, max_value=0.15, value=contam_def, step=0.005,
            help="Valor de referencia para calibrar la detección estadística. 0.03 equivale al 3 %."
        )

        umbral_nlp = st.slider(
            "Umbral de similitud temática",
            min_value=0.30, max_value=0.95, value=nlp_def, step=0.05,
            help="Coincidencia mínima entre descripciones para activar la regla temática."
        )

    with col2:
        ventana_dias = st.selectbox(
            "Ventana de análisis",
            options=list(VENTANAS_DIAS),
            index=list(VENTANAS_DIAS).index(ventana_def) if ventana_def in VENTANAS_DIAS else 1,
            format_func=lambda dias: VENTANAS_DIAS[dias],
            help=(
                "Período para contar compras repetidas del mismo objeto en una entidad. "
                "El tope de 8 UIT se evalúa además por año fiscal, sea cual sea la ventana."
            ),
        )

        # Se muestra en puntos (0-100) y se guarda en escala 0-1, como antes.
        puntos_notificacion = st.slider(
            "Puntaje para notificación de riesgo crítico",
            min_value=50, max_value=95,
            value=int(round(alerta_def * 100 if alerta_def <= 1 else alerta_def)),
            step=5,
            help=(
                "Casos desde este puntaje generan un aviso de riesgo crítico. No cambia "
                "el nivel de riesgo ni la propuesta: el riesgo alto empieza siempre en "
                "71 puntos. Hoy el aviso es simulado (se escribe en el registro del "
                "servidor; no se envía correo)."
            ),
        )
        umbral_alerta = puntos_notificacion / 100.0

    st.divider()

    encabezado_seccion(
        "Flujo de revisión",
        "Define si los casos se clasifican automáticamente o requieren validación manual.",
        "users",
    )
    
    opciones_flujo = ["Automático", "Semiautomático", "Manual"]
    opcion_flujo = st.segmented_control(
        "Flujo aplicado a nuevos casos",
        options=opciones_flujo,
        default=flujo_def if flujo_def in opciones_flujo else opciones_flujo[0],
        width="stretch",
    )
    st.caption(
        "Automático y Semiautomático guardan una propuesta: confirmar desde 71 puntos, "
        "revisar de 41 a 70 y descartar hasta 40. Manual deja todos los expedientes "
        "pendientes. El dictamen final siempre lo registra un auditor."
    )

    st.divider()

    encabezado_seccion(
        "Marco normativo",
        "Valor de referencia utilizado para calcular el límite de ocho UIT.",
        "shield",
    )

    col_uit1, col_uit2 = st.columns([1, 1])

    with col_uit1:
        monto_uit = st.number_input(
            "UIT de respaldo (PEN)",
            min_value=4000.00, max_value=7000.00, value=uit_def, step=50.00,
            help=(
                "El análisis usa la UIT oficial del año de cada convocatoria "
                "(2015-2026). Este valor solo se aplica a años sin UIT oficial registrada."
            ),
        )

    with col_uit2:
        umbral_8uit = monto_uit * 8.0
        st.info(
            f"**Umbral Legal Referencial (8 UIT): S/ {umbral_8uit:,.2f}**\n\n"
            "Las compras menores o iguales a 8 UIT están exentas de la Ley de Contrataciones "
            "pero sujetas a control de fraccionamiento."
        )

    from utilidades.gestor_permisos import tiene_permiso

    if tiene_permiso("cambiar_configuracion"):
        if st.button("Guardar configuración", type="primary", width="stretch"):
            st.session_state['flujo_revision_activo'] = opcion_flujo
            session = obtener_session()
            try:
                session.execute(text("""
                    INSERT INTO configuracion_sistema (frecuencia_contaminacion, umbral_similitud_nlp, ventana_dias, monto_uit_vigente, umbral_alerta_notificacion, flujo_revision)
                    VALUES (:contam, :nlp, :vent, :uit, :alert, :flujo)
                """), {
                    "contam": contaminacion,
                    "nlp": umbral_nlp,
                    "vent": ventana_dias,
                    "uit": monto_uit,
                    "alert": umbral_alerta,
                    "flujo": opcion_flujo,
                })
                session.commit()
                st.cache_data.clear()

                id_usr = st.session_state.get('usuario_id', 1)
                registrar_log(
                    id_usr,
                    "Actualización de configuración",
                    "Configuración",
                    (
                        f"Parámetros actualizados: proporción={contaminacion}, "
                        f"similitud={umbral_nlp:.2f}, ventana={ventana_dias} días, "
                        f"UIT=S/ {monto_uit}, flujo={opcion_flujo}, "
                        f"notificación desde {puntos_notificacion} puntos."
                    ),
                )

                st.success(
                    f"Configuración guardada. Modo activo: {opcion_flujo}; "
                    f"notificaciones de riesgo crítico desde {puntos_notificacion} puntos."
                )
            except Exception as e:
                session.rollback()
                st.error(f"Error al guardar configuración: {e}")
            finally:
                session.close()
    else:
        st.warning("Tu rol no permite modificar los parámetros del sistema.")

    # El panel se muestra solo si se activa en el .env: mientras no haya datos
    # suficientes el modelo permanece inactivo y no afecta a ningún puntaje.
    if os.getenv("MOSTRAR_APRENDIZAJE_SUPERVISADO", "no").strip().lower() in ("si", "sí", "true", "1"):
        st.divider()
        _renderizar_aprendizaje_supervisado()


def _renderizar_aprendizaje_supervisado() -> None:
    """Estado, validación y activación del modelo que aprende de los casos."""
    from utilidades.gestor_permisos import tiene_permiso

    encabezado_seccion(
        "Aprendizaje supervisado",
        "Modelo que aprende de las etiquetas y los dictámenes acumulados. Solo puede "
        "activarse si supera al puntaje actual con entidades que no vio al entrenar.",
        "brain",
    )
    engine = obtener_engine()
    try:
        activo = modelo_activo(engine)
        casos = cargar_casos(engine)
    except Exception as error:
        st.error(f"No fue posible consultar el aprendizaje supervisado: {error}")
        return

    if activo is None:
        st.info("Estado: **inactivo**. Los puntajes se calculan con reglas + ajuste estadístico.")
    else:
        st.success(f"Estado: **activo** (modelo {activo[0]}). Puntúa las nuevas cargas.")

    positivos = int((casos["referencia"] == 1).sum())
    negativos = int((casos["referencia"] == 0).sum())
    entidades_negativas = casos.loc[casos["referencia"] == 0, "entidad_ruc"].nunique()
    col1, col2, col3 = st.columns(3)
    with col1:
        tarjeta_metrica(
            "Casos con fraccionamiento", f"{positivos:,}",
            f"Mínimo {MIN_CASOS_POSITIVOS}", "shield",
        )
    with col2:
        tarjeta_metrica(
            "Casos conformes", f"{negativos:,}",
            f"Mínimo {MIN_CASOS_NEGATIVOS}", "shield",
        )
    with col3:
        tarjeta_metrica(
            "Entidades con casos conformes", f"{entidades_negativas:,}",
            f"Mínimo {MIN_ENTIDADES_NEGATIVAS}", "users",
        )
    st.caption(
        "Cuentan las etiquetas de los archivos cargados y los dictámenes registrados por "
        "un auditor en todos los lotes; una compra cargada varias veces cuenta una vez."
    )

    if not tiene_permiso("cambiar_configuracion"):
        return

    if st.button("Entrenar y validar", width="stretch"):
        with st.spinner("Validando con entidades no vistas…"):
            st.session_state["validacion_supervisada"] = validar(casos)
    validacion = st.session_state.get("validacion_supervisada")

    if validacion is not None:
        if validacion.modelo:
            st.dataframe(
                pd.DataFrame(
                    [
                        {"modelo": "Puntaje actual (reglas + ajuste)", **validacion.actual},
                        {"modelo": "Modelo supervisado", **validacion.modelo},
                    ]
                ).round(3),
                hide_index=True,
                width="stretch",
            )
        if validacion.supera:
            st.success("El modelo supera al puntaje actual en la validación por entidades.")
            if activo is None and st.button("Activar modelo supervisado", type="primary"):
                id_modelo = activar(engine, casos, validacion)
                registrar_log(
                    st.session_state.get("id_usuario", 1),
                    "Activación de modelo supervisado",
                    "Configuración",
                    f"Modelo {id_modelo} activado: {validacion.modelo}.",
                )
                st.session_state.pop("validacion_supervisada", None)
                st.rerun()
        else:
            st.warning(f"Permanece inactivo. {validacion.motivo}")

    if activo is not None and st.button("Desactivar modelo supervisado"):
        desactivar(engine)
        registrar_log(
            st.session_state.get("id_usuario", 1),
            "Desactivación de modelo supervisado",
            "Configuración",
            f"Modelo {activo[0]} desactivado; vuelve el puntaje de reglas + ajuste.",
        )
        st.rerun()
