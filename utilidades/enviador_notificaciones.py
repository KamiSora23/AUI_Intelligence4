import datetime

def enviar_alerta_riesgo_critico(id_convocatoria: int, ruc_entidad: str, nombre_entidad: str, puntaje_riesgo: float, monto: float):
    """
    Simula el envío de una notificación de alerta inmediata (Correo Electrónico / Webhook)
    cuando se detecta una convocatoria con Puntaje de Riesgo mayor al umbral crítico.
    A prueba de errores de codificación cp1252 en consolas de Windows.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje = (
        f"[ALERTA DE RIESGO CRÍTICO SEACE] [{timestamp}]\n"
        f"Se ha detectado un posible fraccionamiento severo:\n"
        f"- Convocatoria ID: #{id_convocatoria}\n"
        f"- Entidad: {nombre_entidad} (RUC: {ruc_entidad})\n"
        f"- Monto Referencial: S/ {monto:,.2f}\n"
        f"- Puntaje de riesgo: {puntaje_riesgo:.1f}\n"
        f"Se requiere revisión inmediata por parte de Auditoría."
    )
    try:
        print(mensaje)
    except Exception:
        pass
    return True
