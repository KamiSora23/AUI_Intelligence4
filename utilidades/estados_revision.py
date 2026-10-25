"""Textos de presentación del estado de revisión y de la ventana de un lote."""

from __future__ import annotations

import re
from collections.abc import Iterable

_PROPUESTAS = {
    "Propuesta_Confirmado": "Propuesta de confirmar",
    "Propuesta_Descartado": "Propuesta de descartar",
}
_DICTAMENES = {
    "Confirmado_Fraccionamiento": "fraccionamiento confirmado",
    "Descartado": "descartado",
}
_EXPLICACIONES = {
    "Propuesta_Confirmado": (
        "Propuesta automática pendiente de evaluación y dictamen del auditor. "
        "No constituye una confirmación de fraccionamiento."
    ),
    "Propuesta_Descartado": (
        "El sistema propone descartar la alerta según sus reglas actuales. "
        "La propuesta no sustituye el dictamen del auditor."
    ),
}
# El motor escribe la ventana aplicada en el motivo de recurrencia.
_PATRON_VENTANA = re.compile(r"compras en (\d+) días")
# Valor que usa el extractor cuando no hay compra anterior comparable.
SIN_COMPRA_ANTERIOR = 999


def describir_estado_revision(estado, con_auditor: bool) -> tuple[str, str]:
    """Devuelve la etiqueta y la aclaración visibles de un estado de revisión.

    Confirmado o descartado solo es dictamen si lo registró un auditor: los
    lotes procesados con versiones anteriores del flujo automático guardaban
    esos estados sin intervención humana.
    """
    estado = str(estado or "Pendiente")
    if estado in _PROPUESTAS:
        return _PROPUESTAS[estado], "Falta el dictamen del auditor"
    if estado in _DICTAMENES:
        if con_auditor:
            return f"Dictamen: {_DICTAMENES[estado]}", "Registrado por el auditor"
        return (
            f"Clasificación automática: {_DICTAMENES[estado]}",
            "Sin dictamen del auditor",
        )
    return "Pendiente de revisión", "Sin propuesta ni dictamen del auditor"


def explicar_estado_revision(estado, con_auditor: bool) -> str:
    """Frase que separa la decisión provisional del sistema del dictamen."""
    estado = str(estado or "Pendiente")
    if estado in _EXPLICACIONES:
        return _EXPLICACIONES[estado]
    if estado in _DICTAMENES:
        if con_auditor:
            return "El auditor registró el dictamen de este expediente."
        return (
            "Clasificación asignada automáticamente por una versión anterior "
            "del flujo; no consta dictamen del auditor."
        )
    return "El expediente espera la revisión del auditor."


def nivel_de_puntaje(puntaje: float) -> str:
    """Nivel de riesgo con los mismos límites que la ingesta (71 y 41 puntos)."""
    if puntaje >= 71.0:
        return "Alto"
    if puntaje >= 41.0:
        return "Medio"
    return "Bajo"


def titulo_informe(estado, con_auditor: bool, puntaje: float) -> str:
    """Encabezado del dossier: nunca presenta una propuesta como conclusión."""
    nivel = nivel_de_puntaje(puntaje).lower()
    estado = str(estado or "Pendiente")
    if estado == "Propuesta_Confirmado":
        return f"Propuesta de revisión por riesgo {nivel}"
    if estado == "Propuesta_Descartado":
        return f"Propuesta del sistema: descartar · riesgo {nivel}"
    etiqueta, _ = describir_estado_revision(estado, con_auditor)
    return f"{etiqueta} · riesgo {nivel}"


def texto_separacion(dias) -> str:
    """Separación respecto de la compra previa, sin mostrar el valor centinela."""
    if dias is None or int(dias) >= SIN_COMPRA_ANTERIOR:
        return "Sin compra anterior registrada"
    dias = int(dias)
    return "1 día" if dias == 1 else f"{dias} días"


def ventana_desde_explicaciones(explicaciones: Iterable) -> int | None:
    """Recupera la ventana que el motor dejó escrita en los motivos del puntaje."""
    for texto in explicaciones:
        coincidencia = _PATRON_VENTANA.search(str(texto or ""))
        if coincidencia:
            return int(coincidencia.group(1))
    return None


def texto_ventana(ventana_dias: int | None) -> str:
    """Expresa la ventana para insertarla en frases como 'operaciones en …'."""
    return f"{int(ventana_dias)} días" if ventana_dias else "la ventana"
