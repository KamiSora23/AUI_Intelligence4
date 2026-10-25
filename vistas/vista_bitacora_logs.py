import streamlit as st
import pandas as pd
from base_datos.gestor_logs import obtener_logs
from vistas.componentes_ui import (
    celda_apilada,
    encabezado_pagina,
    encabezado_seccion,
    resumen_tabla,
    tabla_responsiva,
    texto_seguro,
)


@st.cache_data(ttl=15, show_spinner=False)
def _cargar_logs(limite: int):
    """Evita repetir la misma consulta mientras el usuario navega."""
    return obtener_logs(limite=limite)

def renderizar_vista_logs():
    """Presenta la bitácora operativa ordenada por fecha."""
    encabezado_pagina(
        "Registro de actividad",
        "Trazabilidad de accesos, operaciones administrativas y decisiones de auditoría.",
        "activity",
        "Control y cumplimiento",
    )

    encabezado_seccion("Eventos recientes", "Consulta cronológica de acciones registradas.", "filter")

    limite = st.slider("Número de registros a mostrar", min_value=10, max_value=200, value=50, step=10)
    
    logs = _cargar_logs(limite)

    if not logs:
        st.info("No hay eventos registrados en el período seleccionado.")
    else:
        df_logs = pd.DataFrame(logs)
        filas_logs = []
        for _, fila in df_logs.iterrows():
            fecha = pd.to_datetime(fila.get("fecha"), errors="coerce")
            fecha_texto = (
                fecha.strftime("%d/%m/%Y %H:%M:%S")
                if not pd.isna(fecha)
                else "Sin fecha"
            )
            filas_logs.append(
                [
                    celda_apilada(fecha_texto, f"Evento #{fila.get('id_log', '—')}"),
                    celda_apilada(
                        fila.get("nombre_usuario", "Sistema"),
                        fila.get("rol", "Sin rol"),
                    ),
                    celda_apilada(
                        fila.get("accion", "Evento"),
                        fila.get("modulo", "General"),
                    ),
                    texto_seguro(fila.get("detalle", "Sin detalle")),
                    texto_seguro(fila.get("ip_origen", "Local")),
                ]
            )
        with st.container(border=True):
            resumen_tabla(
                len(df_logs),
                "Los eventos se presentan del más reciente al más antiguo.",
                "eventos",
            )
            tabla_responsiva(
                ["Fecha", "Usuario", "Evento", "Detalle", "Origen"],
                filas_logs,
                ["18%", "19%", "20%", "33%", "10%"],
                "Registro de actividad",
            )
