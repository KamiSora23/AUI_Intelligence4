"""Motor de reglas normativas para la detección de fraccionamiento.

Una contratación se considera relacionada con otra cuando pertenece a la misma
entidad y comparte objeto: mismo código CUBSO o descripciones suficientemente
similares. Solo las operaciones relacionadas se cuentan y se acumulan; comprar
cosas distintas en la misma semana no constituye fraccionamiento.

El monto se acumula por ejercicio fiscal (año de la convocatoria), que es el
período en que se evalúa el límite de 8 UIT. La ventana de días solo mide la
frecuencia de compras cercanas en el tiempo.
"""

import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from modulos_ia.procesador_nlp import limpiar_texto_nfd
from utilidades.fechas import parsear_fechas

# Valor oficial de la UIT por año (D.S. del MEF; 2026: D.S. 301-2025-EF).
# El umbral de 8 UIT debe calcularse con la UIT del año de la convocatoria.
UIT_POR_ANIO = {
    2015: 3850.0, 2016: 3950.0, 2017: 4050.0, 2018: 4150.0, 2019: 4200.0,
    2020: 4300.0, 2021: 4400.0, 2022: 4600.0, 2023: 4950.0, 2024: 5150.0,
    2025: 5350.0, 2026: 5500.0,
}

# Procesos competitivos o excepciones legales excluidos del análisis.
PROCESOS_EXCLUIDOS = [
    "LICITACIÓN PÚBLICA", "LICITACION PUBLICA",
    "CONCURSO PÚBLICO", "CONCURSO PUBLICO",
    "SUBASTA INVERSA ELECTRÓNICA", "SUBASTA INVERSA ELECTRONICA",
    "COMPARACIÓN DE PRECIOS", "COMPARACION DE PRECIOS",
    "EXCEPCIÓN LEGAL DE NO FRACCIONAMIENTO", "EXCEPCION LEGAL DE NO FRACCIONAMIENTO",
    "SUPUESTO LEGAL",
]

# Se comparan contra texto con acentos removidos pero SIN quitar stopwords,
# porque frases como "indebida contratacion" contienen palabras vacías.
PALABRAS_CLAVE_AUDITORIA = [
    'fraccionamiento', 'fraccionar', 'subdivision', 'subdividir',
    'evadir', 'indebida contratacion', 'inobservancia', 'incumplimiento',
    'sobreprecio', 'plagio', 'direccionamiento', 'reajustado indebidamente',
]

# Una contratación cuyo monto supera por sí sola el límite de la modalidad
# "igual o menor a 8 UIT" incumple el régimen sin necesidad de más indicios.
PUNTOS_MONTO_INDIVIDUAL = 75
PUNTOS_PALABRA_CLAVE = 60

_CUBSO_NO_INFORMATIVOS = {"", "general", "nan", "none", "null", "0"}
# Marcadores de relleno ("SERVICIOS/BIENES NO DEFINIDOS (SEGÚN INFORME)") que no
# identifican un objeto y no deben relacionar compras entre sí.
_PATRON_CUBSO_NO_DEFINIDO = "no definid"
_TAMANO_BLOQUE = 2_000_000  # celdas por matriz temporal (acota la memoria)


def _texto_basico(texto) -> str:
    """Minúsculas, sin diacríticos y con espacios colapsados."""
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto.lower()).strip()


def es_resumen_de_hallazgo(df: pd.DataFrame) -> pd.Series:
    """Marca las filas que describen un hallazgo en vez de una compra.

    Se exigen DOS señales a la vez: el texto trae una palabra de auditoría
    ("Fraccionamiento en la contratación de...") Y el CUBSO es un marcador de
    relleno ("SERVICIOS/BIENES NO DEFINIDOS (SEGÚN INFORME)"). Cada señal sola
    es insuficiente: una compra real puede tener el CUBSO sin definir, y una
    descripción puede contener una palabra clave por casualidad (por ejemplo
    "software ANTIPLAGIO"). Esas filas siguen evaluándose como compras.
    """
    if 'descripcion_item' in df.columns:
        texto = df['descripcion_item'].astype(str).apply(_texto_basico)
        con_palabra = texto.apply(lambda t: any(k in t for k in PALABRAS_CLAVE_AUDITORIA))
    else:
        con_palabra = pd.Series(False, index=df.index)
    if 'codigo_cubso' in df.columns:
        sin_cubso = df['codigo_cubso'].astype(str).str.lower().str.contains(
            _PATRON_CUBSO_NO_DEFINIDO, regex=False)
    else:
        sin_cubso = pd.Series(False, index=df.index)
    return con_palabra & sin_cubso


def _ruc_valido(ruc: str) -> bool:
    ruc = str(ruc).strip()
    return bool(ruc) and ruc.lower() != "nan" and set(ruc) != {"0"}


def _uit_por_fila(anios: np.ndarray, uit_vigente: float, tabla: dict) -> np.ndarray:
    return np.array(
        [tabla.get(int(a), uit_vigente) if np.isfinite(a) else uit_vigente for a in anios],
        dtype=float,
    )


def _claves_de_entidad(df: pd.DataFrame) -> list:
    """Agrupa por RUC; si falta o es un marcador de relleno, por nombre."""
    rucs = df['entidad_ruc'].astype(str) if 'entidad_ruc' in df.columns else pd.Series([''] * len(df), index=df.index)
    col_nombre = 'entidad_nombre' if 'entidad_nombre' in df.columns else 'entidad'
    nombres = df[col_nombre].astype(str) if col_nombre in df.columns else pd.Series([''] * len(df), index=df.index)
    claves = []
    for pos, (ruc, nombre) in enumerate(zip(rucs, nombres)):
        if _ruc_valido(ruc):
            claves.append(f"RUC:{ruc.strip()}")
            continue
        nombre_norm = limpiar_texto_nfd(nombre)
        claves.append(f"NOMBRE:{nombre_norm}" if nombre_norm else f"FILA:{pos}")
    return claves


def calcular_scoring_reglas(
    df: pd.DataFrame,
    sim_matrix: np.ndarray = None,
    uit_vigente: float = 5150.0,
    ventana_dias: int = 30,
    umbral_similitud_nlp: float = 0.50,
    uit_por_anio: dict = None,
    usar_etiqueta_auditada: bool = False,
    usar_palabras_clave: bool = False,
) -> pd.DataFrame:
    """Calcula el puntaje reglado (0 a 80) y su explicación para cada operación.

    uit_por_anio: tabla año -> UIT. Por defecto la oficial; ``uit_vigente`` se
        usa para los años que no figuren en la tabla. Pase ``{}`` para forzar un
        único valor.
    usar_etiqueta_auditada: si es True y existe ``es_fraccionamiento``, esa
        etiqueta reemplaza al análisis. Debe permanecer en False para medir el
        desempeño real del motor.
    usar_palabras_clave: si es True, una palabra como "fraccionamiento" en la
        descripción suma puntos. Está desactivada porque en datos de informes
        de control el texto ya trae el hallazgo escrito, lo que revela la
        etiqueta en vez de detectarla; en datos de contratación (SEACE) esas
        palabras no aparecen.
    sim_matrix: matriz opcional (n x n, mismo orden que ``df``) de similitud.
    """
    df_work = df.copy().reset_index(drop=True)
    n = len(df_work)
    tabla_uit = UIT_POR_ANIO if uit_por_anio is None else uit_por_anio

    # --- Tipo de proceso y exclusiones normativas ---------------------------
    col_proceso = next(
        (c for c in ('tipoprocesoseleccion', 'tipo_proceso', 'proceso_seleccion', 'tipo_seleccion')
         if c in df_work.columns),
        None,
    )
    if col_proceso:
        df_work['proceso_clean'] = df_work[col_proceso].astype(str).str.upper().str.strip()
    else:
        df_work['proceso_clean'] = "DESCONOCIDO"
    excluido = df_work['proceso_clean'].apply(
        lambda p: any(exc in p for exc in PROCESOS_EXCLUIDOS)
    ).to_numpy(dtype=bool)
    df_work['es_excluido_normativa'] = excluido

    # --- Variables base ------------------------------------------------------
    monto = pd.to_numeric(df_work['monto_referencial'], errors='coerce').fillna(0.0).to_numpy(dtype=float)
    fechas = parsear_fechas(df_work['fecha_convocatoria'])
    dias = (fechas - pd.Timestamp('1970-01-01')).dt.days.to_numpy(dtype=float)  # NaN si fecha inválida
    anios = fechas.dt.year.to_numpy(dtype=float)
    fecha_ok = np.isfinite(dias)

    uit_fila = _uit_por_fila(anios, uit_vigente, tabla_uit)
    umbral_8 = 8.0 * uit_fila

    col_cubso = 'codigo_cubso' if 'codigo_cubso' in df_work.columns else (
        'itemcubso' if 'itemcubso' in df_work.columns else None)
    if col_cubso:
        cubso_txt = df_work[col_cubso].astype(str).str.strip().str.lower()
        cubso_ok = ~(cubso_txt.isin(_CUBSO_NO_INFORMATIVOS)
                     | cubso_txt.str.contains(_PATRON_CUBSO_NO_DEFINIDO, regex=False))
        cubso_id = np.where(cubso_ok, pd.factorize(cubso_txt)[0], -1)
    else:
        cubso_id = np.full(n, -1)

    desc_original = df_work['descripcion_item'].astype(str) if 'descripcion_item' in df_work.columns \
        else pd.Series([''] * n)
    desc_basica = desc_original.apply(_texto_basico).tolist()
    desc_limpia = desc_original.apply(limpiar_texto_nfd).tolist()
    proceso_clean = df_work['proceso_clean'].tolist()

    # --- Resultados ----------------------------------------------------------
    score = np.zeros(n)
    frecuencia = np.ones(n, dtype=int)
    monto_ventana = monto.copy()
    monto_anual = monto.copy()
    dias_previos = np.full(n, 999, dtype=int)
    max_simil = np.zeros(n)
    explicaciones = [""] * n
    motivos = [[] for _ in range(n)]

    # Reglas que no dependen de otras operaciones.
    for i in range(n):
        if excluido[i]:
            continue
        if usar_palabras_clave and any(kw in desc_basica[i] for kw in PALABRAS_CLAVE_AUDITORIA):
            score[i] += PUNTOS_PALABRA_CLAVE
            motivos[i].append(
                f"Hallazgo de auditoría / Contraloría en descripción (+{PUNTOS_PALABRA_CLAVE})")
        if monto[i] > umbral_8[i] and "8 UIT" in proceso_clean[i]:
            score[i] += PUNTOS_MONTO_INDIVIDUAL
            motivos[i].append(
                f"Monto individual S/{monto[i]:,.2f} supera 8 UIT (S/{umbral_8[i]:,.2f}) "
                f"en modalidad <=8 UIT (+{PUNTOS_MONTO_INDIVIDUAL})"
            )
        if not fecha_ok[i]:
            motivos[i].append("Fecha inválida: no se evaluó recurrencia")

    # --- Reglas relacionales, por entidad -----------------------------------
    elegible = (~excluido) & fecha_ok
    claves = _claves_de_entidad(df_work)
    grupos = pd.Series(range(n)).groupby(pd.Series(claves)).indices
    umbral_alto = max(0.70, umbral_similitud_nlp)

    for _, idx_grupo in grupos.items():
        pool = np.array([i for i in idx_grupo if elegible[i]], dtype=int)
        m = len(pool)
        if m == 0:
            continue
        d, y, mt, cb = dias[pool], anios[pool], monto[pool], cubso_id[pool]

        # Similitud TF-IDF (filas normalizadas L2 -> producto punto = coseno).
        X = None
        if sim_matrix is None and m > 1:
            try:
                X = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(
                    [desc_limpia[i] for i in pool]
                )
            except ValueError:
                X = None  # textos sin vocabulario útil

        bloque = max(1, min(m, _TAMANO_BLOQUE // m))
        for ini in range(0, m, bloque):
            fin = min(ini + bloque, m)
            filas = np.arange(ini, fin)
            c = fin - ini

            if sim_matrix is not None:
                sim = np.asarray(sim_matrix)[np.ix_(pool[ini:fin], pool)].astype(float)
            elif X is not None:
                sim = (X[ini:fin] @ X.T).toarray()
            else:
                sim = np.zeros((c, m))
            sim[np.arange(c), filas] = 0.0  # sin autosimilitud

            propio = np.zeros((c, m), dtype=bool)
            propio[np.arange(c), filas] = True

            dif = d[None, :] - d[ini:fin, None]            # >0: la otra es posterior
            en_ventana = (np.abs(dif) <= ventana_dias) & ~propio
            mismo_anio = (y[ini:fin, None] == y[None, :]) & ~propio
            mismo_cubso = (cb[ini:fin, None] == cb[None, :]) & (cb[ini:fin, None] >= 0) & ~propio
            relacionada = mismo_cubso | (sim >= umbral_similitud_nlp)

            rel_ventana = en_ventana & relacionada
            rel_anual = mismo_anio & relacionada
            n_ventana = rel_ventana.sum(axis=1)
            n_anual = rel_anual.sum(axis=1)
            suma_ventana = mt[ini:fin] + rel_ventana.astype(float) @ mt
            suma_anual = mt[ini:fin] + rel_anual.astype(float) @ mt
            s_max = np.where(en_ventana | mismo_anio, sim, 0.0).max(axis=1)
            con_cubso = (mismo_cubso & rel_anual).any(axis=1)
            previas = (rel_ventana | rel_anual) & (dif <= 0)
            dif_prev = np.where(previas, -dif, np.inf).min(axis=1)

            for k in range(c):
                i = pool[ini + k]
                pts = 0
                hay_recurrencia = n_ventana[k] > 0 or n_anual[k] > 0
                if hay_recurrencia:
                    pts += 15
                    motivos[i].append(
                        f"Recurrencia del mismo objeto: {n_ventana[k] + 1} compras en "
                        f"{ventana_dias} días y {n_anual[k] + 1} en el año fiscal "
                        f"{int(anios[i])} (+15)")
                if n_anual[k] > 0 and suma_anual[k] > umbral_8[i]:
                    pts += 25
                    motivos[i].append(
                        f"Acumulado anual S/{suma_anual[k]:,.2f} supera 8 UIT "
                        f"(S/{umbral_8[i]:,.2f}, UIT {int(anios[i])}) (+25)")
                if con_cubso[k]:
                    pts += 15
                    motivos[i].append("Mismo CUBSO (+15)")
                if s_max[k] >= umbral_alto:
                    pts += 25
                    motivos[i].append(f"Similitud temática alta ({s_max[k] * 100:.1f}%) (+25)")
                elif s_max[k] >= umbral_similitud_nlp:
                    pts += 18
                    motivos[i].append(f"Similitud temática relevante ({s_max[k] * 100:.1f}%) (+18)")

                score[i] += pts
                frecuencia[i] = int(n_ventana[k]) + 1
                monto_ventana[i] = suma_ventana[k]
                monto_anual[i] = suma_anual[k]
                max_simil[i] = s_max[k]
                if np.isfinite(dif_prev[k]):
                    dias_previos[i] = int(dif_prev[k])

    # --- Cierre --------------------------------------------------------------
    score = np.minimum(score, 80.0)
    for i in range(n):
        if excluido[i]:
            explicaciones[i] = "Exento: proceso competitivo regulado o excepción legal"
        else:
            explicaciones[i] = "; ".join(motivos[i]) if motivos[i] else "Sin indicios de fraccionamiento"

    # Atajo opcional con la etiqueta auditada (solo para reproducir hallazgos).
    if usar_etiqueta_auditada and 'es_fraccionamiento' in df_work.columns:
        etiqueta = pd.to_numeric(df_work['es_fraccionamiento'], errors='coerce')
        for i in range(n):
            if etiqueta.iloc[i] == 0:
                score[i], max_simil[i] = 0.0, 0.0
                explicaciones[i] = "Operación auditada: Sin fraccionamiento (Conforme)"
            elif etiqueta.iloc[i] == 1:
                score[i] = 85.0
                explicaciones[i] = "Operación auditada Contraloría: Fraccionamiento confirmado (Hallazgo)"

    df_work['score_reglas_negocio'] = score
    df_work['frecuencia_compras_30d'] = frecuencia
    df_work['monto_acumulado_30d'] = monto_ventana
    df_work['monto_acumulado_anual'] = monto_anual
    df_work['dias_desde_compra_anterior'] = dias_previos
    df_work['similitud_nlp'] = max_simil
    df_work['max_similitud_nlp'] = max_simil
    df_work['umbral_8uit_aplicado'] = umbral_8
    df_work['ratio_monto_8uit'] = monto_anual / np.where(umbral_8 > 0, umbral_8, 1.0)
    df_work['explicacion_reglas'] = explicaciones
    return df_work


def extraer_caracteristicas_temporales_y_nlp(
    df_convocatorias: pd.DataFrame,
    ventana_dias: int = 30,
    uit_vigente: float = 5150.0,
    umbral_similitud_nlp: float = 0.50,
    uit_por_anio: dict = None,
    usar_etiqueta_auditada: bool = False,
    usar_palabras_clave: bool = False,
) -> pd.DataFrame:
    """Expone el cálculo de variables temporales, normativas y léxicas."""
    return calcular_scoring_reglas(
        df_convocatorias,
        uit_vigente=uit_vigente,
        ventana_dias=ventana_dias,
        umbral_similitud_nlp=umbral_similitud_nlp,
        uit_por_anio=uit_por_anio,
        usar_etiqueta_auditada=usar_etiqueta_auditada,
        usar_palabras_clave=usar_palabras_clave,
    )
