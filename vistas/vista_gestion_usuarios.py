import streamlit as st
import bcrypt
import pandas as pd
from sqlalchemy import text

from base_datos.conexion_bd import obtener_session
from base_datos.gestor_logs import registrar_log
from utilidades.gestor_permisos import MATRIZ_PERMISOS
from vistas.componentes_ui import (
    celda_apilada,
    encabezado_pagina,
    encabezado_seccion,
    estado_html,
    resumen_tabla,
    tabla_responsiva,
    texto_seguro,
)


@st.cache_data(ttl=30, show_spinner=False)
def _cargar_directorio_usuarios() -> pd.DataFrame:
    """Conserva el directorio en memoria entre interacciones de la interfaz."""
    session = obtener_session()
    try:
        filas = session.execute(
            text(
                """
                SELECT id_usuario, nombre_completo, nombre_usuario, rol, estado,
                       fecha_creacion
                FROM usuarios
                ORDER BY id_usuario DESC
                """
            )
        ).fetchall()
        return (
            pd.DataFrame([dict(fila._mapping) for fila in filas])
            if filas
            else pd.DataFrame()
        )
    finally:
        session.close()

def renderizar_vista_gestion_usuarios():
    """Abre la administración de cuentas y permisos."""
    mostrar_vista_gestion_usuarios(None, registrar_log)

def mostrar_vista_gestion_usuarios(conexion_bd=None, registrar_log_func=None):
    """
    Renderiza la vista de administración RBAC: Creación de usuarios con Bcrypt,
    modificación de permisos/estados y matriz institucional de control de accesos.
    """
    if registrar_log_func is None:
        registrar_log_func = registrar_log

    encabezado_pagina(
        "Usuarios y accesos",
        "Administra cuentas, roles y políticas de acceso a las funciones de la plataforma.",
        "users",
        "Administración",
    )

    tab1, tab2, tab3 = st.tabs([
        "Nueva cuenta",
        "Directorio",
        "Políticas de acceso",
    ])

    # PESTAÑA 1: CREAR NUEVO USUARIO
    with tab1:
        encabezado_seccion("Crear cuenta", "Registra un usuario y asigna su nivel de acceso.", "users")
        with st.form("form_nuevo_user", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre Completo*", placeholder="Ej. Carlos Mendoza")
                usuario = st.text_input("Usuario de Acceso*", placeholder="Ej. cmendoza")
                email = st.text_input("Correo Institucional", placeholder="cmendoza@contraloria.gob.pe")
            
            with col2:
                rol = st.selectbox("Rol Asignado*", options=list(MATRIZ_PERMISOS.keys()))
                st.info(f"**Privilegios:** {MATRIZ_PERMISOS[rol]['descripcion']}")
                clave = st.text_input("Contraseña*", type="password", placeholder="••••••••")

            btn_crear = st.form_submit_button("Crear cuenta", width="stretch")

            if btn_crear:
                if not nombre or not usuario or not clave:
                    st.error("Complete todos los campos obligatorios (*).")
                else:
                    # Cifrado Bcrypt
                    salt = bcrypt.gensalt()
                    clave_hash = bcrypt.hashpw(clave.encode('utf-8'), salt).decode('utf-8')
                    
                    session = obtener_session()
                    try:
                        # Verificar si el usuario ya existe
                        res_ex = session.execute(
                            text("SELECT COUNT(*) FROM usuarios WHERE nombre_usuario = :usr"),
                            {"usr": usuario}
                        ).scalar()

                        if res_ex > 0:
                            st.error(f"El usuario {usuario} ya existe.")
                        else:
                            query = """
                                INSERT INTO usuarios (nombre_completo, nombre_usuario, correo, clave_encriptada, rol, estado)
                                VALUES (:nombre, :user, :email, :hash, :rol, 1)
                            """
                            session.execute(text(query), {
                                "nombre": nombre,
                                "user": usuario,
                                "email": email or None,
                                "hash": clave_hash,
                                "rol": rol
                            })
                            session.commit()
                            st.cache_data.clear()

                            registrar_log_func(
                                id_usuario=st.session_state.get('id_usuario', st.session_state.get('usuario_id', 1)),
                                modulo="RBAC",
                                accion="Crear Usuario",
                                detalle=f"Usuario '{usuario}' creado con rol '{rol}'."
                            )
                            st.success(f"Cuenta {usuario} creada con el rol {rol}.")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Error al guardar usuario: {e}")
                    finally:
                        session.close()

    # PESTAÑA 2: LISTA Y MODIFICACIÓN DE USUARIOS
    with tab2:
        encabezado_seccion("Directorio de usuarios", "Cuentas activas e historial de altas.", "users")
        try:
            df_u = _cargar_directorio_usuarios().copy()
            
            if not df_u.empty:
                df_u['estado_texto'] = df_u['estado'].apply(lambda x: 'ACTIVO' if str(x) in ['1', 'ACTIVO'] else 'INACTIVO')
                filas_usuarios = []
                for _, fila in df_u.iterrows():
                    activo = fila["estado_texto"] == "ACTIVO"
                    fecha = pd.to_datetime(fila["fecha_creacion"], errors="coerce")
                    fecha_texto = (
                        fecha.strftime("%d/%m/%Y %H:%M")
                        if not pd.isna(fecha)
                        else "Sin fecha"
                    )
                    filas_usuarios.append(
                        [
                            celda_apilada(
                                fila["nombre_completo"],
                                f"@{fila['nombre_usuario']}",
                                f"Cuenta #{int(fila['id_usuario'])}",
                            ),
                            celda_apilada(fila["rol"], "Perfil institucional"),
                            estado_html(
                                "Activo" if activo else "Inactivo",
                                "low" if activo else "high",
                            ),
                            texto_seguro(fecha_texto),
                        ]
                    )
                with st.container(border=True):
                    resumen_tabla(
                        len(df_u),
                        "Directorio institucional con el estado actual de cada cuenta.",
                        "cuentas",
                    )
                    tabla_responsiva(
                        ["Cuenta", "Rol asignado", "Estado", "Fecha de alta"],
                        filas_usuarios,
                        ["38%", "25%", "15%", "22%"],
                        "Directorio de usuarios",
                    )

                st.markdown("---")
                encabezado_seccion("Modificar acceso", "Actualiza el rol o el estado de una cuenta.", "settings")
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    user_id_mod = st.selectbox(
                        "Seleccionar Usuario", 
                        options=df_u['id_usuario'].tolist(),
                        format_func=lambda x: f"ID #{x} - {df_u.loc[df_u['id_usuario']==x, 'nombre_usuario'].values[0]}"
                    )
                with col_s2:
                    nuevo_rol = st.selectbox("Nuevo Rol", options=list(MATRIZ_PERMISOS.keys()))
                with col_s3:
                    nuevo_estado_txt = st.selectbox("Estado", options=["ACTIVO", "INACTIVO"])
                    nuevo_estado_val = 1 if nuevo_estado_txt == "ACTIVO" else 0

                if st.button("Guardar cambios", width="stretch"):
                    session_u = obtener_session()
                    try:
                        session_u.execute(
                            text("UPDATE usuarios SET rol = :rol, estado = :est WHERE id_usuario = :id"),
                            {"rol": nuevo_rol, "est": nuevo_estado_val, "id": user_id_mod}
                        )
                        session_u.commit()
                        st.cache_data.clear()
                        
                        registrar_log_func(
                            id_usuario=st.session_state.get('id_usuario', 1),
                            modulo="RBAC",
                            accion="Modificar Usuario",
                            detalle=f"Usuario ID #{user_id_mod} actualizado a rol '{nuevo_rol}' y estado '{nuevo_estado_txt}'."
                        )
                        st.success("El acceso de la cuenta fue actualizado.")
                        st.rerun()
                    except Exception as e:
                        session_u.rollback()
                        st.error(f"Error al actualizar permisos: {e}")
                    finally:
                        session_u.close()
            else:
                st.info("No hay otros usuarios registrados en el sistema.")
        except Exception as e:
            st.error(f"Error al cargar lista de usuarios: {e}")

    # PESTAÑA 3: VER MATRIZ DE PERMISOS
    with tab3:
        encabezado_seccion(
            "Políticas de acceso",
            "Funciones y operaciones habilitadas para cada rol.",
            "shield",
        )
        datos = []
        for r, info in MATRIZ_PERMISOS.items():
            datos.append({
                "Rol": r,
                "Descripción": info["descripcion"],
                "Vistas Autorizadas": ", ".join(info["vistas"]),
                "Acciones Permitidas": ", ".join(info["acciones"])
            })
        with st.container(border=True):
            resumen_tabla(
                len(datos),
                "Resumen de alcance funcional por perfil institucional.",
                "roles",
            )
            tabla_responsiva(
                ["Rol", "Descripción", "Vistas autorizadas", "Acciones permitidas"],
                [
                    [
                        celda_apilada(fila["Rol"], "Perfil de acceso"),
                        texto_seguro(fila["Descripción"]),
                        texto_seguro(fila["Vistas Autorizadas"]),
                        texto_seguro(fila["Acciones Permitidas"]),
                    ]
                    for fila in datos
                ],
                ["17%", "27%", "28%", "28%"],
                "Políticas de acceso",
            )
