"""Resolución diferida de vistas para reducir el costo de arranque."""

from __future__ import annotations

from importlib import import_module
from typing import Callable


RUTAS_VISTAS = {
    "vista_panel_principal": (
        "vistas.vista_panel_principal",
        "renderizar_vista_dashboard",
    ),
    "vista_carga_datos": (
        "vistas.vista_carga_datos",
        "renderizar_vista_carga",
    ),
    "vista_detalle_auditoria": (
        "vistas.vista_detalle_auditoria",
        "renderizar_vista_detalle",
    ),
    "vista_configuracion": (
        "vistas.vista_configuracion",
        "renderizar_vista_configuracion",
    ),
    "vista_estadisticas_globales": (
        "vistas.vista_estadisticas_globales",
        "renderizar_vista_estadisticas",
    ),
    "vista_bitacora_logs": (
        "vistas.vista_bitacora_logs",
        "renderizar_vista_logs",
    ),
    "vista_gestion_usuarios": (
        "vistas.vista_gestion_usuarios",
        "renderizar_vista_gestion_usuarios",
    ),
}


def resolver_vista(vista: str) -> Callable[[], None]:
    """Importa y devuelve exclusivamente la vista solicitada."""
    modulo, funcion = RUTAS_VISTAS.get(
        vista,
        RUTAS_VISTAS["vista_panel_principal"],
    )
    return getattr(import_module(modulo), funcion)
