"""Selector compartido del lote activo entre las vistas analíticas."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from base_datos.conexion_bd import obtener_engine
from utilidades.estados_revision import ventana_desde_explicaciones


@st.cache_data(ttl=30, show_spinner=False)
def ventana_del_lote(lote_id: int) -> int | None:
    """Ventana de recurrencia con la que se procesó el lote.

    Los lotes anteriores a la columna ``ventana_dias`` la recuperan de los
    motivos del puntaje. Sin ninguna de las dos fuentes devuelve ``None``: la
    configuración actual podría no ser la que se aplicó.
    """
    with obtener_engine().connect() as conn:
        ventana = conn.execute(
            text("SELECT ventana_dias FROM historial_cargas WHERE id_carga = :lote"),
            {"lote": lote_id},
        ).scalar()
        if ventana:
            return int(ventana)
        explicaciones = conn.execute(
            text(
                """
                SELECT r.explicacion_reglas
                FROM resultados_anomalias r
                JOIN convocatorias_procesadas c
                    ON r.id_convocatoria = c.id_convocatoria
                WHERE c.id_carga = :lote
                  AND r.explicacion_reglas LIKE '%compras en % días%'
                LIMIT 1
                """
            ),
            {"lote": lote_id},
        ).scalars()
        return ventana_desde_explicaciones(explicaciones)


@st.cache_data(ttl=30, show_spinner=False)
def _cargar_lotes() -> pd.DataFrame:
    """Recupera una lista breve reutilizable durante la navegación."""
    with obtener_engine().connect() as conn:
        return pd.read_sql(
            """
            SELECT id_carga, nombre_archivo, total_registros, fecha_carga
            FROM historial_cargas
            ORDER BY id_carga DESC
            """,
            conn,
        )


def renderizar_selector_lote_global(
    conexion_bd=None,
    clave_componente: str = "selector_global",
) -> int | None:
    """Renderiza el selector de lotes y sincroniza ``lote_activo_id``.

    ``clave_componente`` se conserva por compatibilidad con llamadas existentes;
    todas las vistas comparten deliberadamente una única clave de estado.
    """
    try:
        if conexion_bd is None or conexion_bd is obtener_engine():
            df_lotes = _cargar_lotes().copy()
        else:
            with conexion_bd.connect() as conn:
                df_lotes = pd.read_sql(
                    """
                    SELECT id_carga, nombre_archivo, total_registros, fecha_carga
                    FROM historial_cargas
                    ORDER BY id_carga DESC
                    """,
                    conn,
                )
    except Exception as error:
        st.error(f"No fue posible consultar los archivos procesados: {error}")
        return None

    if df_lotes.empty:
        st.warning("No hay archivos ni lotes procesados en el sistema.")
        return None

    opciones = {
        int(fila["id_carga"]): (
            f"{fila['nombre_archivo']} · Lote {int(fila['id_carga'])} · "
            f"{str(fila['fecha_carga'])[:16]} · "
            f"{int(fila['total_registros']):,} registros"
        )
        for _, fila in df_lotes.iterrows()
    }
    ids = list(opciones)
    lote_actual = st.session_state.get("lote_activo_id", ids[0])
    lote_actual = int(lote_actual) if lote_actual in ids else ids[0]
    if st.session_state.get("lote_activo_id") != lote_actual:
        st.session_state["lote_activo_id"] = lote_actual

    seleccionado = int(
        st.selectbox(
            "Archivo de expedientes / Archivo analizado",
            options=ids,
            format_func=opciones.__getitem__,
            index=ids.index(lote_actual),
            key="lote_activo_id",
            help=(
                "Cambie el archivo para sincronizar Expediente, Inteligencia "
                "Ejecutiva y las demás vistas enlazadas."
            ),
        )
    )
    return seleccionado
