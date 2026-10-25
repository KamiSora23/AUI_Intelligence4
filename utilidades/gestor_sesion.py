"""Persistencia segura de la sesión web entre recargas del navegador."""

from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import extra_streamlit_components as stx
import jwt
import streamlit as st

from base_datos.conexion_bd import (
    obtener_usuario_activo_por_id,
    registrar_sesion_web,
    revocar_sesion_web,
    sesion_web_activa,
)


NOMBRE_COOKIE = "aui_session"
DURACION_SESION_DIAS = 7
EMISOR_TOKEN = "aui-intelligence"


def crear_gestor_cookies(key: str = "aui_session_cookie_manager"):
    """Crea el único puente de cookies utilizado durante una ejecución."""
    return stx.CookieManager(key=key)


def guardar_sesion_persistente(gestor_cookies, usuario: dict) -> str | None:
    """Firma una referencia de sesión y la conserva en el navegador."""
    if gestor_cookies is None:
        return None

    ahora = datetime.now(timezone.utc)
    vencimiento = ahora + timedelta(days=DURACION_SESION_DIAS)
    id_sesion = uuid4().hex
    contenido = {
        "sub": str(usuario["id_usuario"]),
        "jti": id_sesion,
        "iat": ahora,
        "exp": vencimiento,
        "iss": EMISOR_TOKEN,
    }
    registrar_sesion_web(
        id_sesion,
        int(usuario["id_usuario"]),
        vencimiento.replace(tzinfo=None),
    )
    token = jwt.encode(contenido, _obtener_clave_firma(), algorithm="HS256")
    gestor_cookies.set(
        NOMBRE_COOKIE,
        token,
        key="aui_session_set",
        path="/",
        expires_at=vencimiento.replace(tzinfo=None),
        same_site="strict",
        secure=False,
    )
    return id_sesion


def restaurar_sesion_persistente(gestor_cookies) -> bool:
    """Restaura la identidad si el token es válido y la cuenta sigue activa."""
    if st.session_state.get("usuario_autenticado"):
        return True
    token = _leer_cookie_sesion(gestor_cookies)
    if not token:
        return False

    try:
        contenido = jwt.decode(
            token,
            _obtener_clave_firma(),
            algorithms=["HS256"],
            issuer=EMISOR_TOKEN,
        )
        id_usuario = int(contenido["sub"])
        id_sesion = str(contenido["jti"])
        if not sesion_web_activa(id_sesion, id_usuario):
            eliminar_sesion_persistente(gestor_cookies, revocar=False)
            return False

        usuario = obtener_usuario_activo_por_id(id_usuario)
        if not usuario:
            eliminar_sesion_persistente(gestor_cookies)
            return False
        cargar_usuario_en_sesion(usuario, id_sesion)
        return True
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        eliminar_sesion_persistente(gestor_cookies)
        return False


def eliminar_sesion_persistente(gestor_cookies, revocar: bool = True) -> None:
    """Revoca la sesión guardada en el navegador."""
    token = _leer_cookie_sesion(gestor_cookies)
    if token:
        if revocar:
            try:
                contenido = jwt.decode(
                    token,
                    _obtener_clave_firma(),
                    algorithms=["HS256"],
                    issuer=EMISOR_TOKEN,
                )
                revocar_sesion_web(str(contenido["jti"]))
            except (jwt.PyJWTError, KeyError, TypeError, ValueError):
                pass
        if gestor_cookies is None:
            gestor_cookies = crear_gestor_cookies("aui_session_cookie_cleanup")
        try:
            gestor_cookies.delete(NOMBRE_COOKIE, key="aui_session_delete")
        except KeyError:
            # El componente ya envió la orden de borrado al navegador, pero
            # una instancia creada en este ciclo aún no conoce su caché local.
            pass


def revocar_sesion_actual() -> None:
    """Revoca la sesión activa sin depender de un componente del navegador."""
    id_sesion = st.session_state.get("id_sesion_web")
    if id_sesion:
        revocar_sesion_web(str(id_sesion))


def cargar_usuario_en_sesion(
    usuario: dict,
    id_sesion: str | None = None,
) -> None:
    """Mantiene una sola definición de las claves de identidad de Streamlit."""
    st.session_state["usuario_autenticado"] = True
    st.session_state["usuario_id"] = usuario["id_usuario"]
    st.session_state["id_usuario"] = usuario["id_usuario"]
    st.session_state["usuario_nombre"] = usuario["nombre_usuario"]
    st.session_state["nombre_completo"] = usuario.get(
        "nombre_completo",
        usuario["nombre_usuario"],
    )
    st.session_state["usuario_rol"] = usuario["rol"]
    st.session_state["rol_usuario"] = usuario["rol"]
    if id_sesion:
        st.session_state["id_sesion_web"] = id_sesion


def _leer_cookie_sesion(gestor_cookies=None) -> str | None:
    """Lee la cookie desde la solicitud y usa el componente como respaldo."""
    try:
        token = st.context.cookies.get(NOMBRE_COOKIE)
        if token:
            return str(token)
    except (AttributeError, RuntimeError):
        pass

    if gestor_cookies is None:
        return None
    token = gestor_cookies.get(NOMBRE_COOKIE)
    return str(token) if token else None


def _obtener_clave_firma() -> str:
    clave = os.getenv("SECRET_KEY", "").strip()
    if not clave:
        raise RuntimeError(
            "SECRET_KEY debe estar configurada para firmar las sesiones persistentes."
        )
    return clave
