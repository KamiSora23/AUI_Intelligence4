"""Lectura de fechas sin ambigüedad entre formatos ISO y día/mes/año."""

from __future__ import annotations

import re

import pandas as pd

_PATRON_ISO = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}")


def parsear_fechas(valores) -> pd.Series:
    """Convierte una serie de fechas a ``datetime64``; las inválidas quedan NaT.

    Las cadenas ISO (``2026-03-08``) se leen siempre como año-mes-día. Con
    ``dayfirst=True`` aplicado a todo, ciertas versiones de pandas intercambian
    mes y día en esas cadenas (03-08 pasa a ser el 3 de agosto). Las demás
    (``08/03/2026``) se interpretan como día/mes/año, formato usual en Perú.
    """
    serie = valores if isinstance(valores, pd.Series) else pd.Series(valores)
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie
    texto = serie.astype(str).str.strip()
    es_iso = texto.str.match(_PATRON_ISO)
    iso = pd.to_datetime(texto.where(es_iso), format="ISO8601", errors="coerce")
    otras = pd.to_datetime(
        texto.where(~es_iso), format="mixed", dayfirst=True, errors="coerce"
    )
    return iso.fillna(otras)
