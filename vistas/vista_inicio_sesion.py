from textwrap import dedent
from time import sleep

import streamlit as st

from base_datos.conexion_bd import autenticar_usuario
from base_datos.gestor_logs import registrar_log
from utilidades.gestor_sesion import (
    cargar_usuario_en_sesion,
    guardar_sesion_persistente,
)
from vistas.componentes_ui import marca_svg, visual_acceso_svg


def renderizar_vista_login(gestor_cookies=None) -> None:
    """Muestra el acceso principal y delega la validación en la capa de datos."""
    mostrar_vista_inicio_sesion(
        autenticar_usuario,
        registrar_log,
        gestor_cookies,
    )


def mostrar_vista_inicio_sesion(
    autenticar_usuario_func,
    registrar_log_func,
    gestor_cookies=None,
) -> None:
    """Construye un acceso institucional sobrio y adaptable."""
    contexto, acceso = st.columns(
        [1.28, 0.72],
        gap="large",
        vertical_alignment="center",
    )

    with contexto:
        st.markdown(
            dedent(
                f"""
                <div class="auth-context">
                    <div class="auth-context__brand">
                        {marca_svg("auth-context__mark")}
                        <div>
                            <strong>AUI Intelligence</strong>
                            <span>Control de contrataciones</span>
                        </div>
                    </div>
                    <div class="auth-context__copy">
                        <span class="auth-context__index">01 / ACCESO SEGURO</span>
                        <h1>Auditoría preventiva.<br><em>Evidencia antes que intuición.</em></h1>
                        <p>
                            Detecta recurrencias, contrasta montos y documenta cada
                            decisión desde un único espacio de trabajo.
                        </p>
                    </div>
                    <div class="auth-map">
                        {visual_acceso_svg()}
                        <div class="auth-map__scan"></div>
                    </div>
                    <div class="auth-context__footer">
                        <span><i></i>Servicios disponibles</span>
                        <span>Entorno institucional</span>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with acceso:
        with st.form("login_form", clear_on_submit=False):
            st.markdown(
                dedent(
                    f"""
                    <div class="auth-form-header">
                        {marca_svg("auth-form-header__mark")}
                        <span>IDENTIFICACIÓN</span>
                        <h2>Bienvenido</h2>
                        <p>Utiliza las credenciales asignadas a tu perfil.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
            usuario = st.text_input(
                "Usuario",
                placeholder="Nombre de usuario",
                key="input_usuario",
            )
            clave = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Contraseña",
                key="input_clave",
            )
            submit_button = st.form_submit_button(
                "Ingresar",
                icon=":material/arrow_forward:",
                width="stretch",
            )

            if submit_button:
                if not usuario or not clave:
                    st.warning("Completa el usuario y la contraseña.")
                else:
                    usuario_db = autenticar_usuario_func(usuario, clave)
                    if usuario_db:
                        _iniciar_sesion(usuario_db)
                        id_sesion = guardar_sesion_persistente(
                            gestor_cookies,
                            usuario_db,
                        )
                        if id_sesion:
                            st.session_state["id_sesion_web"] = id_sesion
                        _registrar_acceso(registrar_log_func, usuario_db)
                        # El componente debe completar la escritura de la cookie.
                        # La pausa breve permite entregar la orden al navegador
                        # antes de iniciar el ciclo que muestra el panel.
                        sleep(0.35)
                        st.rerun()
                    else:
                        st.error("Las credenciales ingresadas no son válidas.")

        st.markdown(
            """
            <div class="auth-form-footer">
                <span>Acceso por rol</span>
                <span>Sesión auditada</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _iniciar_sesion(usuario_db: dict) -> None:
    """Centraliza las claves de sesión utilizadas por las vistas."""
    cargar_usuario_en_sesion(usuario_db)


def _registrar_acceso(registrar_log_func, usuario_db: dict) -> None:
    """Registra el acceso sin bloquear la sesión si la bitácora no responde."""
    try:
        registrar_log_func(
            id_usuario=usuario_db["id_usuario"],
            accion="Inicio de sesión",
            modulo="Autenticación",
            detalle=(
                f"Acceso correcto del usuario {usuario_db['nombre_usuario']} "
                f"con rol {usuario_db['rol']}."
            ),
        )
    except Exception:
        # La autenticación no depende de la disponibilidad temporal de la bitácora.
        pass
