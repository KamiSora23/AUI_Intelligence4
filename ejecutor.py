from textwrap import dedent

import streamlit as st

st.set_page_config(
    page_title="AUI Intelligence | Control de contrataciones",
    page_icon="assets/aui-mark.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

import vistas.estilo_css as estilo_css
from base_datos.conexion_bd import obtener_engine
from base_datos.sembrador_datos import poblar_datos_semilla
from utilidades.gestor_permisos import obtener_vistas_permitidas
from utilidades.enrutador_vistas import resolver_vista
from utilidades.gestor_sesion import (
    crear_gestor_cookies,
    eliminar_sesion_persistente,
    revocar_sesion_actual,
    restaurar_sesion_persistente,
)
from vistas.componentes_ui import marca_svg
from vistas.vista_inicio_sesion import renderizar_vista_login


VISTAS = {
    "Centro de control": "vista_panel_principal",
    "Ingesta de datos": "vista_carga_datos",
    "Expedientes": "vista_detalle_auditoria",
    "Modelo y parámetros": "vista_configuracion",
    "Inteligencia ejecutiva": "vista_estadisticas_globales",
    "Registro de actividad": "vista_bitacora_logs",
    "Usuarios y accesos": "vista_gestion_usuarios",
}

ICONOS_NAVEGACION = {
    "vista_panel_principal": ":material/space_dashboard:",
    "vista_carga_datos": ":material/cloud_upload:",
    "vista_detalle_auditoria": ":material/folder_open:",
    "vista_configuracion": ":material/tune:",
    "vista_estadisticas_globales": ":material/monitoring:",
    "vista_bitacora_logs": ":material/history:",
    "vista_gestion_usuarios": ":material/admin_panel_settings:",
}


@st.cache_resource(show_spinner=False)
def _preparar_recursos() -> bool:
    """Ejecuta las verificaciones costosas una sola vez por proceso."""
    obtener_engine()
    poblar_datos_semilla()
    return True


def inicializar_aplicacion() -> None:
    """Prepara estilos, conexión y estado mínimo de la sesión."""
    estilo_css.aplicar_estilos_modernos()
    _preparar_recursos()

    st.session_state.setdefault("usuario_autenticado", False)
    st.session_state.setdefault("vista_actual", "vista_panel_principal")
    st.session_state.setdefault("modo_automatico_hil", True)
    st.session_state.setdefault("menu_compacto", True)


def _alternar_menu() -> None:
    st.session_state["menu_compacto"] = not st.session_state.get(
        "menu_compacto",
        True,
    )


def _cambiar_vista(vista: str) -> None:
    st.session_state["vista_actual"] = vista


def renderizar_sidebar(gestor_cookies=None) -> str:
    """Renderiza una única navegación filtrada por el rol activo."""
    menu_compacto = bool(st.session_state.get("menu_compacto", True))

    with st.sidebar:
        if menu_compacto:
            st.markdown(
                """
                <style>
                html body .stApp section[data-testid="stSidebar"] {
                    width: 60px !important;
                    min-width: 60px !important;
                    max-width: 60px !important;
                    transform: none !important;
                }
                html body .stApp section[data-testid="stSidebar"] > div:first-child {
                    width: 60px !important;
                    padding: .36rem .3rem .55rem !important;
                    overflow-x: hidden !important;
                }
                html body .stApp section[data-testid="stSidebar"] .sidebar-brand {
                    justify-content: center;
                    padding: .26rem 0 .42rem;
                }
                html body .stApp section[data-testid="stSidebar"] .sidebar-brand > div,
                html body .stApp section[data-testid="stSidebar"] .user-card,
                html body .stApp section[data-testid="stSidebar"] .sidebar-nav-label,
                html body .stApp section[data-testid="stSidebar"] hr {
                    display: none !important;
                }
                html body .stApp section[data-testid="stSidebar"] .brand-mark {
                    width: 30px !important;
                    height: 30px !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton {
                    margin: 0 0 .1rem !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton button {
                    display: flex !important;
                    grid-template-columns: none !important;
                    width: 40px !important;
                    min-width: 40px !important;
                    min-height: 40px !important;
                    justify-content: center !important;
                    gap: 0 !important;
                    margin: 0 auto !important;
                    padding: 0 !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton button > div {
                    width: auto !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton button > div > span {
                    display: flex !important;
                    justify-content: center !important;
                    width: auto !important;
                    gap: 0 !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton button p,
                html body .stApp section[data-testid="stSidebar"] .stButton button [data-testid="stMarkdownContainer"] {
                    display: none !important;
                }
                html body .stApp section[data-testid="stSidebar"] .stButton button span[data-testid="stIconMaterial"] {
                    margin: 0 !important;
                    font-size: 1rem !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

        st.button(
            "Expandir navegación" if menu_compacto else "Reducir navegación",
            icon=(
                ":material/left_panel_open:"
                if menu_compacto
                else ":material/left_panel_close:"
            ),
            key="alternar_menu",
            help=(
                "Mostrar nombres de las secciones"
                if menu_compacto
                else "Conservar solamente los iconos"
            ),
            width="stretch",
            on_click=_alternar_menu,
        )

        st.markdown(
            dedent(
                f"""
            <div class="sidebar-brand">
                {marca_svg()}
                <div>
                    <div class="sidebar-brand__name">AUI Intelligence</div>
                    <div class="sidebar-brand__meta">Control preventivo</div>
                </div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )

        nombre = st.session_state.get(
            "nombre_completo",
            st.session_state.get("usuario_nombre", "Usuario"),
        )
        rol = st.session_state.get(
            "usuario_rol",
            st.session_state.get("rol_usuario", "Auditor"),
        )
        estado_bd = "MySQL/MariaDB conectado"

        st.markdown(
            dedent(
                f"""
            <div class="user-card">
                <div class="user-title">{nombre}</div>
                <div class="user-role">{rol}</div>
                <div class="connection-line"><span></span>{estado_bd}</div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )

        permitidas = set(obtener_vistas_permitidas())
        opciones = {
            nombre: vista
            for nombre, vista in VISTAS.items()
            if nombre in permitidas
        }
        if not opciones:
            opciones = {"Centro de control": "vista_panel_principal"}

        vista_actual = st.session_state.get("vista_actual", "vista_panel_principal")
        if vista_actual not in opciones.values():
            vista_actual = next(iter(opciones.values()))
            st.session_state["vista_actual"] = vista_actual

        st.markdown(
            '<div class="sidebar-nav-label">Navegación principal</div>',
            unsafe_allow_html=True,
        )
        for nombre, vista in opciones.items():
            activo = vista == vista_actual
            st.button(
                nombre,
                key=f"nav_{vista}",
                icon=ICONOS_NAVEGACION[vista],
                type="primary" if activo else "secondary",
                help=nombre,
                width="stretch",
                on_click=_cambiar_vista,
                args=(vista,),
            )

        st.markdown("---")
        if st.button(
            "Cerrar sesión",
            icon=":material/logout:",
            width="stretch",
            key="cerrar_sesion",
            help="Cerrar la sesión actual",
        ):
            revocar_sesion_actual()
            eliminar_sesion_persistente(gestor_cookies)
            st.session_state.clear()
            st.rerun()

    return st.session_state["vista_actual"]


def renderizar_vista(vista: str) -> None:
    """Resuelve la vista activa desde un mapa explícito y fácil de extender."""
    resolver_vista(vista)()


inicializar_aplicacion()
gestor_cookies = None
if not st.session_state["usuario_autenticado"]:
    restaurar_sesion_persistente(None)

if st.session_state["usuario_autenticado"]:
    renderizar_vista(renderizar_sidebar(gestor_cookies))
else:
    gestor_cookies = crear_gestor_cookies()
    renderizar_vista_login(gestor_cookies)
