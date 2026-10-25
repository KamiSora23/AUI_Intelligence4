import streamlit as st

# Matriz central de permisos por rol.
MATRIZ_PERMISOS = {
    "Administrador": {
        "descripcion": "Acceso total a la plataforma, parámetros, usuarios y registro de actividad.",
        "vistas": [
            "Centro de control",
            "Ingesta de datos",
            "Expedientes",
            "Modelo y parámetros",
            "Inteligencia ejecutiva",
            "Registro de actividad",
            "Usuarios y accesos",
        ],
        "acciones": ["cargar_datos", "dictaminar_caso", "cambiar_configuracion", "crear_usuarios", "exportar_pdf"]
    },
    "Supervisor": {
        "descripcion": "Carga de fuentes, revisión analítica, decisión de casos y consulta de actividad.",
        "vistas": [
            "Centro de control",
            "Ingesta de datos",
            "Expedientes",
            "Inteligencia ejecutiva",
            "Registro de actividad",
        ],
        "acciones": ["cargar_datos", "dictaminar_caso", "exportar_pdf"]
    },
    "Auditor": {
        "descripcion": "Revisión de expedientes, registro de decisiones y descarga de informes.",
        "vistas": [
            "Centro de control",
            "Expedientes",
            "Inteligencia ejecutiva",
        ],
        "acciones": ["dictaminar_caso", "exportar_pdf"]
    },
    "Investigador": {
        "descripcion": "Acceso de solo lectura para consulta de estadísticas e informes generales.",
        "vistas": [
            "Centro de control",
            "Inteligencia ejecutiva",
        ],
        "acciones": ["exportar_pdf"]
    }
}

ROL_SIN_SESION = "Investigador"  # mínimo privilegio si no hay un rol en sesión


def _rol_activo() -> str:
    return st.session_state.get(
        'usuario_rol',
        st.session_state.get('rol_usuario', ROL_SIN_SESION),
    )


def tiene_permiso(accion: str) -> bool:
    """
    Valida si el rol activo en sesión tiene autorización para ejecutar una acción específica.
    """
    acciones_permitidas = MATRIZ_PERMISOS.get(_rol_activo(), {}).get("acciones", [])
    return accion in acciones_permitidas

def obtener_vistas_permitidas() -> list:
    """
    Devuelve la lista de vistas habilitadas para el rol del usuario logueado.
    """
    return MATRIZ_PERMISOS.get(_rol_activo(), {}).get("vistas", ["Centro de control"])
