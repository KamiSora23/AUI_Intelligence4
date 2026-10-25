import bcrypt
from sqlalchemy import text
from base_datos.conexion_bd import obtener_session

# Hash de relleno que dejaban las versiones anteriores de esquema_inicial.sql.
# No corresponde a ninguna contraseña, por lo que se reemplaza al iniciar.
HASH_MARCADOR_SQL = "$2b$12$6/7/LhQ5y6G.G8tq6U2Wle3NnQO5s9aTzJ0W5W9W5W9W5W9W5W9W5"

def poblar_datos_semilla():
    """
    Pabla la base de datos (MySQL o SQLite) con usuarios por defecto, configuración
    y un conjunto inicial de convocatorias procesadas con sus anomalías calculadas.
    """
    session = obtener_session()
    try:
        # 1. Crear únicamente las cuentas iniciales que todavía no existan.
        # Bcrypt es deliberadamente costoso, por lo que nunca se recalculan hashes
        # durante un rerun normal de Streamlit.
        usuarios_existentes = {
            fila[0]
            for fila in session.execute(
                text("SELECT nombre_usuario FROM usuarios")
            ).fetchall()
        }
        usuarios_iniciales = (
            (
                "admin",
                "admin123",
                "Administrador Principal SEACE",
                "admin@contraloria.gob.pe",
                "Administrador",
            ),
            (
                "supervisor",
                "supervisor123",
                "Supervisor de Auditoría OSCE",
                "supervisor@osce.gob.pe",
                "Supervisor",
            ),
            (
                "auditor",
                "auditor123",
                "Auditor de Contrataciones OSCE",
                "auditor@osce.gob.pe",
                "Auditor",
            ),
            (
                "investigador",
                "investigador123",
                "Investigador Institucional",
                "investigador@contraloria.gob.pe",
                "Investigador",
            ),
        )
        for usuario, clave, nombre, correo, rol in usuarios_iniciales:
            if usuario in usuarios_existentes:
                hash_actual = session.execute(
                    text(
                        "SELECT clave_encriptada FROM usuarios "
                        "WHERE nombre_usuario = :usuario"
                    ),
                    {"usuario": usuario},
                ).scalar()
                if hash_actual == HASH_MARCADOR_SQL:
                    session.execute(
                        text(
                            "UPDATE usuarios SET clave_encriptada = :clave "
                            "WHERE nombre_usuario = :usuario"
                        ),
                        {
                            "clave": bcrypt.hashpw(
                                clave.encode("utf-8"),
                                bcrypt.gensalt(),
                            ).decode("utf-8"),
                            "usuario": usuario,
                        },
                    )
                continue
            clave_hash = bcrypt.hashpw(
                clave.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            session.execute(
                text(
                    """
                    INSERT INTO usuarios (
                        nombre_usuario,
                        clave_encriptada,
                        nombre_completo,
                        correo,
                        rol,
                        estado
                    )
                    VALUES (:usuario, :clave, :nombre, :correo, :rol, 1)
                    """
                ),
                {
                    "usuario": usuario,
                    "clave": clave_hash,
                    "nombre": nombre,
                    "correo": correo,
                    "rol": rol,
                },
            )
        session.commit()

        # 2. Configuración inicial
        count_cfg = session.execute(text("SELECT COUNT(*) FROM configuracion_sistema")).scalar()
        if count_cfg == 0:
            session.execute(text("""
                INSERT INTO configuracion_sistema (frecuencia_contaminacion, umbral_similitud_nlp, ventana_dias, monto_uit_vigente, ruta_almacenamiento_pdf, notificar_riesgo_alto, umbral_alerta_notificacion)
                VALUES (0.030, 0.50, 30, 5150.00, './reportes_pdf/', 1, 0.85)
            """))
            session.commit()

        # Modelo de referencia.
        count_mod = session.execute(text("SELECT COUNT(*) FROM modelos_ia")).scalar()
        if count_mod == 0:
            session.execute(text("""
                INSERT INTO modelos_ia (nombre_modelo, metrica_precision, metrica_recall, metrica_f1, metrica_roc_auc, estado_activo)
                VALUES ('Isolation Forest v1.0 (Baseline)', 0.8850, 0.8420, 0.8629, 0.9110, 1)
            """))
            session.commit()

        # Conjunto inicial utilizado para comprobar la instalación.
        count_conv = session.execute(text("SELECT COUNT(*) FROM convocatorias_procesadas")).scalar()
        if count_conv == 0:
            print("[DATOS] Preparando el conjunto inicial de contrataciones.")
            import pandas as pd

            from modulos_ia.extractor_caracteristicas import (
                extraer_caracteristicas_temporales_y_nlp,
            )
            from modulos_ia.modelo_aislamiento import (
                entrenar_y_evaluar_isolation_forest,
            )
            
            # Casos de referencia con operaciones normales y patrones recurrentes.
            dataset_inicial = pd.DataFrame([
                # Procesos competitivos utilizados como casos de control.
                {"entidad_ruc": "20544333124", "entidad_nombre": "CENARES - ABASTECIMIENTO DE RECURSOS ESTRATEGICOS", "descripcion_item": "ADQUISICIÓN CENTRALIZADA DEL MEDICAMENTO NIVOLUMAB 100 MG INYECTABLE PARA LA RED NACIONAL DE SALUD", "monto_referencial": 23540889.00, "fecha_convocatoria": "2026-02-15", "codigo_cubso": "51101501", "tipo_proceso": "Licitación Pública"},

                {"entidad_ruc": "20100012345", "entidad_nombre": "MINISTERIO DE EDUCACION", "descripcion_item": "CONTRATACION DE SERVICIO DE LIMPIEZA INTEGRAL DE SEDE CENTRAL", "monto_referencial": 180000.00, "fecha_convocatoria": "2026-01-15", "codigo_cubso": "76111501", "tipo_proceso": "Concurso Público"},

                # Contrataciones directas recurrentes de Agro Rural.
                {"entidad_ruc": "20477936882", "entidad_nombre": "PROGRAMA AGRO RURAL - MINAGRI", "descripcion_item": "ADQUISICION DE ALIMENTO SUPLEMENTARIO PARA GANADO HENO PELLET TIPO A", "monto_referencial": 280320.00, "fecha_convocatoria": "2024-04-18", "codigo_cubso": "10121501", "tipo_proceso": "Contratación Directa"},
                {"entidad_ruc": "20477936882", "entidad_nombre": "PROGRAMA AGRO RURAL - MINAGRI", "descripcion_item": "ADQUISICION DE ALIMENTO SUPLEMENTARIO PARA GANADO HENO PELLET TIPO B", "monto_referencial": 236060.00, "fecha_convocatoria": "2024-04-18", "codigo_cubso": "10121501", "tipo_proceso": "Contratación Directa"},
                {"entidad_ruc": "20477936882", "entidad_nombre": "PROGRAMA AGRO RURAL - MINAGRI", "descripcion_item": "ADQUISICION DE ALIMENTO SUPLEMENTARIO PARA GANADO HENO PELLET GRANULADO", "monto_referencial": 588759.00, "fecha_convocatoria": "2024-04-19", "codigo_cubso": "10121501", "tipo_proceso": "Contratación Directa"},
                {"entidad_ruc": "20477936882", "entidad_nombre": "PROGRAMA AGRO RURAL - MINAGRI", "descripcion_item": "ADQUISICION DE ALIMENTO SUPLEMENTARIO HENO PELLET PARA EMERGENCIA AGRARIA", "monto_referencial": 644760.00, "fecha_convocatoria": "2024-04-22", "codigo_cubso": "10121501", "tipo_proceso": "Contratación Directa"},
                {"entidad_ruc": "20477936882", "entidad_nombre": "PROGRAMA AGRO RURAL - MINAGRI", "descripcion_item": "ADQUISICION DE ALIMENTO SUPLEMENTARIO GANADERO HENO PELLET EN SACOS", "monto_referencial": 712000.00, "fecha_convocatoria": "2024-04-25", "codigo_cubso": "10121501", "tipo_proceso": "Contratación Directa"},
                
                # Compras recurrentes de la Municipalidad del Callao.
                {"entidad_ruc": "20131378901", "entidad_nombre": "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "descripcion_item": "ADQUISICIÓN DE PAPEL BOND A4 DE 75G PARA OFICINAS ADMINISTRATIVAS", "monto_referencial": 38500.00, "fecha_convocatoria": "2026-03-01", "codigo_cubso": "44121506", "tipo_proceso": "Igual o Menor a 8 UIT"},
                {"entidad_ruc": "20131378901", "entidad_nombre": "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "descripcion_item": "ADQUISICION DE PAPEL BOND A4 75 GR PARA GERENCIA DE LOGISTICA", "monto_referencial": 39200.00, "fecha_convocatoria": "2026-03-05", "codigo_cubso": "44121506", "tipo_proceso": "Igual o Menor a 8 UIT"},
                {"entidad_ruc": "20131378901", "entidad_nombre": "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "descripcion_item": "COMPRA DE PAPEL BOND BLANCO TAMANO A4 PARA SUBGERENCIA", "monto_referencial": 37900.00, "fecha_convocatoria": "2026-03-12", "codigo_cubso": "44121506", "tipo_proceso": "Igual o Menor a 8 UIT"},
                {"entidad_ruc": "20131378901", "entidad_nombre": "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "descripcion_item": "SUMINISTRO DE PAPEL BOND A4 IMPRESIONES VARIAS", "monto_referencial": 38100.00, "fecha_convocatoria": "2026-03-18", "codigo_cubso": "44121506", "tipo_proceso": "Igual o Menor a 8 UIT"},
                
                # Adjudicaciones simplificadas del Hospital Dos de Mayo.
                {"entidad_ruc": "20504789123", "entidad_nombre": "HOSPITAL NACIONAL DOS DE MAYO", "descripcion_item": "ADQUISICION DE MASCARILLAS QUIRURGICAS TRIPLE CAPA", "monto_referencial": 25000.00, "fecha_convocatoria": "2026-02-10", "codigo_cubso": "42131606", "tipo_proceso": "Adjudicación Simplificada"},
                {"entidad_ruc": "20504789123", "entidad_nombre": "HOSPITAL NACIONAL DOS DE MAYO", "descripcion_item": "ADQUISICION DE MASCARILLAS QUIRURGICAS DE PROTECCION ATERIAL", "monto_referencial": 24800.00, "fecha_convocatoria": "2026-02-14", "codigo_cubso": "42131606", "tipo_proceso": "Adjudicación Simplificada"},
                {"entidad_ruc": "20504789123", "entidad_nombre": "HOSPITAL NACIONAL DOS DE MAYO", "descripcion_item": "MASCARILLA DESECHABLE TRIPLE CAPA CON EMBALAJE HERMETICO", "monto_referencial": 26200.00, "fecha_convocatoria": "2026-02-20", "codigo_cubso": "42131606", "tipo_proceso": "Adjudicación Simplificada"},
                
                # Otras compras normales
                {"entidad_ruc": "20100012345", "entidad_nombre": "MINISTERIO DE EDUCACION", "descripcion_item": "ADQUISICION DE MOBILIARIO ESCOLAR PARA INSTITUCION EDUCATIVA EMBLAMATICA", "monto_referencial": 350000.00, "fecha_convocatoria": "2026-02-01", "codigo_cubso": "56121502", "tipo_proceso": "Subasta Inversa Electrónica"},
                {"entidad_ruc": "20131378901", "entidad_nombre": "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "descripcion_item": "SERVICIO DE MANTENIMIENTO PREVENTIVO DE COMPUTADORAS DE ESCRITORIO", "monto_referencial": 41000.00, "fecha_convocatoria": "2026-03-15", "codigo_cubso": "81111802", "tipo_proceso": "Adjudicación Simplificada"},
                {"entidad_ruc": "20222333444", "entidad_nombre": "GOBIERNO REGIONAL DE AREQUIPA", "descripcion_item": "ADQUISICION DE ASFALTO LIQUIDO RC-250 PARA OBRAS VIALES", "monto_referencial": 520000.00, "fecha_convocatoria": "2026-01-20", "codigo_cubso": "30111505", "tipo_proceso": "Licitación Pública"}
            ])

            # Ejecuta el mismo flujo que utiliza la ingesta.
            df_feats = extraer_caracteristicas_temporales_y_nlp(dataset_inicial, ventana_dias=30)
            df_res, modelo, scaler = entrenar_y_evaluar_isolation_forest(df_feats, contaminacion=0.03)

            # Insertar en historial_cargas
            session.execute(text("""
                INSERT INTO historial_cargas (nombre_archivo, total_registros, id_usuario)
                VALUES ('DATASET_SEMILLA_INICIAL_SEACE.xlsx', :tot, 1)
            """), {"tot": len(df_res)})
            session.commit()

            id_carga = session.execute(text("SELECT MAX(id_carga) FROM historial_cargas")).scalar() or 1
            id_modelo = session.execute(text("SELECT id_modelo FROM modelos_ia WHERE estado_activo = 1 LIMIT 1")).scalar() or 1

            for _, row in df_res.iterrows():
                session.execute(text("""
                    INSERT INTO convocatorias_procesadas (id_carga, entidad_ruc, entidad_nombre, descripcion_item, monto_referencial, fecha_convocatoria, codigo_cubso, tipo_proceso)
                    VALUES (:id_c, :ruc, :nom, :desc, :monto, :fec, :cubso, :tipo_p)
                """), {
                    "id_c": id_carga,
                    "ruc": str(row['entidad_ruc']),
                    "nom": str(row['entidad_nombre']),
                    "desc": str(row['descripcion_item']),
                    "monto": float(row['monto_referencial']),
                    "fec": str(row['fecha_convocatoria'])[:10],
                    "cubso": str(row.get('codigo_cubso', 'GENERAL')),
                    "tipo_p": str(row.get('tipo_proceso', 'Igual o Menor a 8 UIT'))
                })
                session.commit()

                id_conv = session.execute(text("SELECT MAX(id_convocatoria) FROM convocatorias_procesadas")).scalar()

                session.execute(text("""
                    INSERT INTO resultados_anomalias (id_convocatoria, id_modelo, similitud_nlp, monto_acumulado_30d, frecuencia_compras_30d, dias_desde_compra_anterior, score_reglas_negocio, bono_ia, puntaje_riesgo, nivel_riesgo, es_anomalia, explicacion_reglas, estado_revision)
                    VALUES (:id_conv, :id_mod, :nlp, :monto_30, :freq_30, :dias_ant, :score_reg, :bono, :score, :nivel, :es_anom, :exp, 'Pendiente')
                """), {
                    "id_conv": id_conv,
                    "id_mod": id_modelo,
                    "nlp": float(row.get('similitud_nlp', 0.0)),
                    "monto_30": float(row.get('monto_acumulado_30d', 0.0)),
                    "freq_30": int(row.get('frecuencia_compras_30d', 1)),
                    "dias_ant": int(row.get('dias_desde_compra_anterior', 999)),
                    "score_reg": float(row.get('score_reglas_negocio', 0.0)),
                    "bono": float(row.get('bono_ia', 0.0)),
                    "score": float(row.get('puntaje_riesgo', 0.0)),
                    "nivel": str(row.get('nivel_riesgo', 'Bajo')),
                    "es_anom": int(row.get('es_anomalia', 0)),
                    "exp": str(row.get('explicacion_reglas', 'Exento'))
                })
                session.commit()

            print(
                f"[DATOS] Conjunto inicial disponible: {len(df_res)} operaciones."
            )

    except Exception as e:
        session.rollback()
        print(f"[DATOS] No fue posible preparar el conjunto inicial: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    poblar_datos_semilla()
