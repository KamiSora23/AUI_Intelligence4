"""Operaciones puras para paginar resultados sin alterar su contenido."""

from __future__ import annotations

import math

import pandas as pd


def paginar_dataframe(
    datos: pd.DataFrame,
    pagina: int,
    tamano: int = 50,
) -> tuple[pd.DataFrame, int, int]:
    """Devuelve una página, el número normalizado y el total de páginas."""
    if tamano < 1:
        raise ValueError("El tamaño de página debe ser mayor que cero.")

    total_paginas = max(1, math.ceil(len(datos) / tamano))
    pagina_actual = min(max(int(pagina), 1), total_paginas)
    inicio = (pagina_actual - 1) * tamano
    fin = inicio + tamano
    return datos.iloc[inicio:fin].copy(), pagina_actual, total_paginas
