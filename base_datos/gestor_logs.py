from sqlalchemy import text
from base_datos.conexion_bd import obtener_session

def registrar_log(id_usuario: int = 1, accion: str = "Acción", modulo: str = "General", detalle: str = "", ip_origen: str = "127.0.0.1", **kwargs):
    """
    Registra un evento de seguridad o auditoría en la tabla `logs_sistema`.
    Soporta parámetros posicionales y nombrados (id_usuario / usuario_id).
    """
    usr_id = kwargs.get('usuario_id', id_usuario)
    session = obtener_session()
    try:
        query = text("""
            INSERT INTO logs_sistema (id_usuario, accion, modulo, ip_origen, detalle)
            VALUES (:id_usuario, :accion, :modulo, :ip_origen, :detalle)
        """)
        session.execute(query, {
            "id_usuario": usr_id,
            "accion": accion,
            "modulo": modulo,
            "ip_origen": ip_origen,
            "detalle": detalle
        })
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error al registrar log de sistema: {e}")
    finally:
        session.close()

def obtener_logs(limite: int = 100, filtro_usuario: str = None, id_usuario: int = None):
    """
    Obtiene los últimos eventos registrados en la bitácora de logs.
    """
    session = obtener_session()
    try:
        where_clauses = []
        params = {"limite": limite}
        
        if id_usuario:
            where_clauses.append("l.id_usuario = :id_usuario")
            params["id_usuario"] = id_usuario

        where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"""
            SELECT l.id_log, l.fecha, u.nombre_usuario, u.rol, l.modulo, l.accion, l.detalle, l.ip_origen
            FROM logs_sistema l
            LEFT JOIN usuarios u ON l.id_usuario = u.id_usuario
            {where_str}
            ORDER BY l.id_log DESC
            LIMIT :limite
        """
        result = session.execute(text(sql), params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    except Exception as e:
        print(f"Error al recuperar logs: {e}")
        return []
    finally:
        session.close()
