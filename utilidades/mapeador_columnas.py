from datetime import date, datetime
import re
import unicodedata

import pandas as pd
from thefuzz import fuzz

from utilidades.fechas import parsear_fechas

# Diccionario de alias conocidos por columna normalizada
ALIAS_COLUMNAS = {
    "entidad_ruc": [
        "ruc", "ruc_entidad", "entidad_ruc", "ruc entidad", "num_ruc", "nro_ruc", "ruc_comprador"
    ],
    "entidad_nombre": [
        "entidad", "nombre_entidad", "entidad_nombre", "nombre entidad", "razon_social", "denominacion_entidad", "entidad contratante"
    ],
    "descripcion_item": [
        "descripcion", "descripcion_item", "descripcion item", "item_descripcion", "objeto_contratacion", "objeto", "detalle_item", "bien_o_servicio"
    ],
    "monto_referencial": [
        "monto", "monto_referencial", "monto referencial", "valor_referencial", "monto_adjudicado", "precio_total", "valor_estimado", "monto_total"
    ],
    "fecha_convocatoria": [
        "fecha", "fecha_convocatoria", "fecha convocatoria", "fec_convocatoria", "fecha_publicacion", "fecha_emision", "fecha_registro"
    ],
    "codigo_cubso": [
        "cubso", "itemcubso", "item_cubso", "codigo_cubso", "cod_cubso", "codigo cubso", "catalogo_cubso", "codigo_catalogo"
    ],
    "tipo_proceso": [
        "tipo_proceso", "tipo_proceso_seleccion", "tipo proceso", "modalidad", "modalidad_contratacion", "tipo_seleccion", "proceso_seleccion"
    ],
    "es_fraccionamiento": [
        "es_fraccionamiento", "fraccionamiento", "es_anomalia", "caso_esperado", "label", "etiqueta_fraccionamiento"
    ]
}

def _normalizar_encabezado(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"[^a-z0-9]+", " ", texto.lower())
    return " ".join(texto.split())


def limpiar_cadena_codigo(valor: object) -> str:
    """Elimina decimales espurios (.0) resultantes de la lectura numérica en pandas."""
    if pd.isna(valor) or valor is None:
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def limpiar_ruc(valor: object) -> str:
    """Normaliza y limpia el RUC eliminando ceros decimales, espacios y caracteres no numéricos."""
    texto = limpiar_cadena_codigo(valor)
    digitos = re.sub(r"[^0-9]", "", texto)
    if len(digitos) == 11:
        return digitos
    if len(digitos) > 11:
        return digitos[:11]
    if digitos:
        return digitos
    return texto[:20] if texto else "00000000000"


def normalizar_fecha(valor: object) -> str:
    """Convierte cualquier formato de fecha a string 'YYYY-MM-DD' compatible con MariaDB/MySQL."""
    if pd.isna(valor) or valor is None:
        return pd.Timestamp.now().strftime("%Y-%m-%d")
    if isinstance(valor, (pd.Timestamp, datetime, date)):
        return valor.strftime("%Y-%m-%d")
    val_str = str(valor).strip()
    if not val_str:
        return pd.Timestamp.now().strftime("%Y-%m-%d")
    try:
        dt = parsear_fechas(pd.Series([val_str])).iloc[0]
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    if len(val_str) >= 10 and val_str[4] == "-" and val_str[7] == "-":
        return val_str[:10]
    return pd.Timestamp.now().strftime("%Y-%m-%d")


def limpiar_monto(valor: object) -> float:
    """Limpia valores numéricos, admitiendo strings con símbolos de moneda y separadores."""
    if pd.isna(valor) or valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return 0.0
    texto = re.sub(r"^[^\d\-]+", "", texto).strip()
    texto = re.sub(r"[^\d.,\-]", "", texto)
    if not texto:
        return 0.0
    if "," in texto and "." in texto:
        if texto.rfind(",") < texto.rfind("."):
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto and "." not in texto:
        partes = texto.split(",")
        if len(partes) == 2 and len(partes[1]) in (1, 2):
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")
    try:
        return float(texto)
    except Exception:
        return 0.0


def normalizar_y_emparejar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza los encabezados de una fuente Excel o CSV mediante alias y
    coincidencia aproximada.
    """
    df_normalizado = df.copy()
    columnas_originales = [str(col).strip() for col in df_normalizado.columns]

    candidatos = []
    for col_std, aliases in ALIAS_COLUMNAS.items():
        for col_orig in columnas_originales:
            origen = _normalizar_encabezado(col_orig)
            mejor_score = 0
            for alias in aliases:
                alias_normalizado = _normalizar_encabezado(alias)
                score = fuzz.ratio(origen, alias_normalizado)
                if origen in alias_normalizado or alias_normalizado in origen:
                    score += 20  # Refuerzo cuando un nombre contiene al otro.
                mejor_score = max(mejor_score, score)

            if mejor_score >= 60:
                candidatos.append((mejor_score, col_std, col_orig))

    # Resuelve el mapeo globalmente para que una columna de origen no pueda
    # sobrescribir dos campos normalizados.
    mapeo_final = {}
    campos_asignados = set()
    for _, col_std, col_orig in sorted(candidatos, reverse=True):
        if col_std in campos_asignados or col_orig in mapeo_final:
            continue
        mapeo_final[col_orig] = col_std
        campos_asignados.add(col_std)

    df_normalizado = df_normalizado.rename(columns=mapeo_final)

    cols_requeridas = [
        "entidad_ruc",
        "entidad_nombre",
        "descripcion_item",
        "monto_referencial",
        "fecha_convocatoria",
    ]
    cols_faltantes = [c for c in cols_requeridas if c not in df_normalizado.columns]

    if cols_faltantes:
        faltantes = ", ".join(cols_faltantes)
        raise ValueError(
            f"No se identificaron las columnas obligatorias: {faltantes}."
        )

    # Filas sin ningún dato de compra (filas en blanco con formato o restos de
    # fórmulas al final de la hoja) no son compras: se descartan sin contarlas
    # como omitidas por fecha.
    texto_obligatorio = df_normalizado[cols_requeridas].astype(str).apply(
        lambda columna: columna.str.strip()
    )
    vacias = (
        df_normalizado[cols_requeridas].isna() | texto_obligatorio.isin(["", "nan", "None", "NaT"])
    ).all(axis=1)
    df_normalizado = df_normalizado.loc[~vacias].copy()

    if "entidad_ruc" in df_normalizado.columns:
        df_normalizado["entidad_ruc"] = df_normalizado["entidad_ruc"].apply(limpiar_ruc)

    # Una fecha ausente o ilegible no se sustituye por la de hoy: inventar la
    # fecha crearía relaciones temporales falsas. Esas filas se omiten y el
    # total queda en ``df.attrs['filas_omitidas_fecha']`` para informarlo.
    fechas = parsear_fechas(df_normalizado["fecha_convocatoria"])
    sin_fecha = fechas.isna()
    df_normalizado = df_normalizado.loc[~sin_fecha].copy()
    df_normalizado["fecha_convocatoria"] = fechas.loc[~sin_fecha].dt.strftime("%Y-%m-%d")
    df_normalizado = df_normalizado.reset_index(drop=True)
    df_normalizado.attrs["filas_omitidas_fecha"] = int(sin_fecha.sum())
    df_normalizado.attrs["filas_vacias"] = int(vacias.sum())

    if "monto_referencial" in df_normalizado.columns:
        df_normalizado["monto_referencial"] = df_normalizado["monto_referencial"].apply(limpiar_monto)

    if "codigo_cubso" not in df_normalizado.columns:
        df_normalizado["codigo_cubso"] = "GENERAL"
    else:
        df_normalizado["codigo_cubso"] = df_normalizado["codigo_cubso"].apply(limpiar_cadena_codigo)

    if "tipo_proceso" not in df_normalizado.columns:
        df_normalizado["tipo_proceso"] = "Igual o Menor a 8 UIT"

    return df_normalizado

