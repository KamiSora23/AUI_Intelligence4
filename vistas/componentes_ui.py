import html
from base64 import b64encode
from textwrap import dedent

import streamlit as st


ICONOS = {
    "dashboard": '<path d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z"/>',
    "upload": '<path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 14v5h14v-5"/>',
    "file": '<path d="M6 3h8l4 4v14H6V3Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/>',
    "chart": '<path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/>',
    "activity": '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    "filter": '<path d="M4 5h16l-6 7v5l-4 2v-7L4 5Z"/>',
    "network": '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><path d="m7 7 4 9m6-9-4 9M7 6h10"/>',
    "brain": '<path d="M9.5 4A3.5 3.5 0 0 0 6 7.5V9a3 3 0 0 0-1 5.8V16a4 4 0 0 0 4 4h1V4h-.5Zm5 0A3.5 3.5 0 0 1 18 7.5V9a3 3 0 0 1 1 5.8V16a4 4 0 0 1-4 4h-1V4h.5Z"/><path d="M6 10h4m4 0h4M7 16h3m4 0h3"/>',
    "shield": '<path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
    "lock": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
}


def icono_svg(nombre: str, clase: str = "ui-icon") -> str:
    contenido = ICONOS.get(nombre, ICONOS["shield"])
    relleno = 'fill="currentColor"' if nombre == "dashboard" else 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
    return f'<svg class="{clase}" viewBox="0 0 24 24" aria-hidden="true" {relleno}>{contenido}</svg>'


def marca_svg(clase: str = "brand-mark") -> str:
    svg = dedent(
        """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
        <defs>
            <linearGradient id="auiGradient" x1="4" y1="4" x2="44" y2="44">
                <stop offset="0" stop-color="#8B7CFF"/>
                <stop offset="1" stop-color="#5CDCF4"/>
            </linearGradient>
        </defs>
        <path d="M24 3 42 10v11c0 11.2-7.3 19.4-18 24C13.3 40.4 6 32.2 6 21V10L24 3Z" fill="url(#auiGradient)"/>
        <path d="m15.5 31 7.2-16h2.8l7 16h-4.4l-1.4-3.5h-6.1L19.2 31h-3.7Zm6.5-7h3.3l-1.6-4.5L22 24Z" fill="#fff"/>
        <path d="M13 35h22" stroke="#F2B84B" stroke-width="2.2" stroke-linecap="round"/>
    </svg>
    """
    ).strip()
    contenido = b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        f'<img class="{html.escape(clase)}" alt="AUI" '
        f'src="data:image/svg+xml;base64,{contenido}"/>'
    )


def visual_acceso_svg(clase: str = "auth-map__image") -> str:
    """Construye el mapa técnico que acompaña al acceso institucional."""
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360">
      <defs>
        <linearGradient id="line" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#5CDCF4" stop-opacity=".78"/>
          <stop offset="1" stop-color="#8B7CFF" stop-opacity=".78"/>
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="4" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <g fill="none" stroke="#24334B" stroke-width="1">
        <path d="M20 40H740M20 110H740M20 180H740M20 250H740M20 320H740"/>
        <path d="M80 20V340M200 20V340M320 20V340M440 20V340M560 20V340M680 20V340"/>
      </g>
      <g fill="none" stroke="url(#line)" stroke-width="2">
        <path d="M134 102 300 180 468 88 628 198"/>
        <path d="M300 180 474 278 628 198"/>
      </g>
      <g fill="#09111F" stroke="#334866" stroke-width="1.5">
        <rect x="76" y="70" width="116" height="64" rx="8"/>
        <rect x="248" y="146" width="104" height="68" rx="8"/>
        <rect x="412" y="56" width="112" height="64" rx="8"/>
        <rect x="418" y="246" width="112" height="64" rx="8"/>
        <rect x="574" y="164" width="108" height="68" rx="8"/>
      </g>
      <g font-family="Segoe UI,Arial,sans-serif">
        <g fill="#72839E" font-size="9" font-weight="700" letter-spacing="1.5">
          <text x="94" y="93">ENTIDAD</text>
          <text x="266" y="170">PROCESO</text>
          <text x="430" y="80">MONTO</text>
          <text x="436" y="270">TIEMPO</text>
          <text x="592" y="188">ALERTA</text>
        </g>
        <g fill="#EEF3FA" font-size="17" font-weight="700">
          <text x="94" y="119">RUC validado</text>
          <text x="266" y="197">Recurrente</text>
          <text x="430" y="106">8 UIT</text>
          <text x="436" y="296">30 días</text>
          <text x="592" y="215">88.2 pts</text>
        </g>
      </g>
      <g fill="#5CDCF4" filter="url(#glow)">
        <circle cx="134" cy="102" r="4"/>
        <circle cx="300" cy="180" r="4"/>
        <circle cx="468" cy="88" r="4"/>
        <circle cx="474" cy="278" r="4"/>
      </g>
      <circle cx="628" cy="198" r="6" fill="#8B7CFF" filter="url(#glow)"/>
    </svg>
    """
    contenido = b64encode(dedent(svg).strip().encode("utf-8")).decode("ascii")
    return (
        f'<img class="{html.escape(clase)}" alt="Mapa de señales de auditoría" '
        f'src="data:image/svg+xml;base64,{contenido}"/>'
    )


def encabezado_pagina(titulo: str, descripcion: str, icono: str, etiqueta: str = "AUI Intelligence") -> None:
    st.markdown(
        dedent(
            f"""
        <div class="page-hero">
            <div class="page-hero__identity">
                <div class="page-hero__icon">{icono_svg(icono)}</div>
                <div class="page-hero__content">
                    <span class="eyebrow">{html.escape(etiqueta)}</span>
                    <h1>{html.escape(titulo)}</h1>
                </div>
            </div>
            <p class="page-hero__description">{html.escape(descripcion)}</p>
            <div class="page-hero__status">
                <span class="page-hero__pulse"></span>
                Sesión protegida
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def encabezado_seccion(titulo: str, descripcion: str = "", icono: str = "activity") -> None:
    detalle = f"<p>{html.escape(descripcion)}</p>" if descripcion else ""
    st.markdown(
        dedent(
            f"""
        <div class="section-heading">
            <div class="section-heading__icon">{icono_svg(icono)}</div>
            <div><h2>{html.escape(titulo)}</h2>{detalle}</div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def estado_html(texto: str, tono: str = "neutral") -> str:
    return f'<span class="status-badge status-badge--{tono}"><span></span>{html.escape(texto)}</span>'


def tarjeta_metrica(
    titulo: str,
    valor: str,
    detalle: str,
    icono: str,
    tono: str = "primary",
) -> None:
    """Renderiza un indicador compacto con jerarquía visual consistente."""
    st.markdown(
        dedent(
            f"""
        <div class="metric-card metric-card--{html.escape(tono)}">
            <div class="metric-card__topline">
                <div class="metric-title">{html.escape(titulo)}</div>
                <div class="metric-card__icon">{icono_svg(icono, "ui-icon ui-icon--metric")}</div>
            </div>
            <div class="metric-value">{html.escape(valor)}</div>
            <div class="metric-subtitle">{html.escape(detalle)}</div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def resumen_tabla(total: int, descripcion: str, etiqueta: str = "registros") -> None:
    """Añade una cabecera operativa antes de una matriz de datos."""
    st.markdown(
        dedent(
            f"""
        <div class="data-toolbar">
            <div>
                <span class="data-toolbar__count">{int(total):,}</span>
                <span class="data-toolbar__label">{html.escape(etiqueta)}</span>
            </div>
            <p>{html.escape(descripcion)}</p>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def texto_seguro(valor) -> str:
    """Escapa contenido procedente de archivos o de la base de datos."""
    if valor is None:
        return "—"
    return html.escape(str(valor))


def celda_apilada(
    principal,
    secundario=None,
    metadato=None,
) -> str:
    """Compone una celda multilínea sin truncar información."""
    partes = [f'<strong class="table-cell__primary">{texto_seguro(principal)}</strong>']
    if secundario not in (None, ""):
        partes.append(
            f'<span class="table-cell__secondary">{texto_seguro(secundario)}</span>'
        )
    if metadato not in (None, ""):
        partes.append(
            f'<span class="table-cell__meta">{texto_seguro(metadato)}</span>'
        )
    return "".join(partes)


def tabla_responsiva(
    encabezados: list[str],
    filas: list[list[str]],
    anchos: list[str] | None = None,
    etiqueta: str = "Tabla de datos",
) -> None:
    """Renderiza una tabla de ancho fijo con celdas multilínea y vista móvil."""
    if not filas:
        st.info("No hay registros para mostrar.")
        return

    if anchos and len(anchos) == len(encabezados):
        columnas_html = "".join(
            f'<col style="width:{html.escape(ancho)}">'
            for ancho in anchos
        )
        grupo_columnas = f"<colgroup>{columnas_html}</colgroup>"
    else:
        grupo_columnas = ""

    cabecera_html = "".join(
        f"<th scope='col'>{html.escape(titulo)}</th>"
        for titulo in encabezados
    )
    filas_html = []
    for fila in filas:
        celdas = []
        for indice, titulo in enumerate(encabezados):
            valor = fila[indice] if indice < len(fila) else "—"
            celdas.append(
                f"<td data-label='{html.escape(titulo)}'>{valor}</td>"
            )
        filas_html.append(f"<tr>{''.join(celdas)}</tr>")

    st.markdown(
        dedent(
            f"""
        <div class="responsive-table-shell" role="region"
             aria-label="{html.escape(etiqueta)}">
            <table class="responsive-table">
                {grupo_columnas}
                <thead><tr>{cabecera_html}</tr></thead>
                <tbody>{''.join(filas_html)}</tbody>
            </table>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def estilizar_grafica(figura, altura: int = 350, mostrar_leyenda: bool | None = None):
    """Aplica el lenguaje visual de la aplicación a una figura Plotly."""
    configuracion = {
        "height": altura,
        "margin": {"l": 18, "r": 18, "t": 20, "b": 20},
        "paper_bgcolor": "#111620",
        "plot_bgcolor": "#111620",
        "font": {
            "family": 'Inter, "Segoe UI", sans-serif',
            "color": "#A4ADBD",
            "size": 11,
        },
        "hoverlabel": {
            "bgcolor": "#202738",
            "bordercolor": "#4A556E",
            "font": {"color": "#F8FAFC", "size": 12},
        },
        "colorway": ["#8B7CFF", "#5CDCF4", "#F2B84B", "#FF6F87", "#4DD6A5"],
    }
    if mostrar_leyenda is not None:
        configuracion["showlegend"] = mostrar_leyenda

    figura.update_layout(**configuracion)
    figura.update_xaxes(
        gridcolor="rgba(145, 155, 176, .12)",
        zerolinecolor="rgba(145, 155, 176, .18)",
        linecolor="rgba(145, 155, 176, .18)",
        tickfont={"color": "#9099AA"},
        title_font={"color": "#AEB6C5"},
        automargin=True,
    )
    figura.update_yaxes(
        gridcolor="rgba(145, 155, 176, .12)",
        zerolinecolor="rgba(145, 155, 176, .18)",
        linecolor="rgba(145, 155, 176, .18)",
        tickfont={"color": "#9099AA"},
        title_font={"color": "#AEB6C5"},
        automargin=True,
    )
    return figura
