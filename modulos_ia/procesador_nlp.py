import re
import unicodedata
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Lista expandida de stopwords en español para contrataciones del estado
STOPWORDS_ES = set([
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para',
    'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o',
    'este', 'sí', 'porque', 'esta', 'entre', 'cuando', 'muy', 'sin', 'sobre', 'también',
    'me', 'hasta', 'hay', 'donde', 'quien', 'desde', 'todo', 'nos', 'durante', 'todos',
    'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto',
    'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto',
    'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar',
    'estas', 'algunas', 'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu', 'tus',
    'adquisicion', 'adquisición', 'servicio', 'servicios', 'contratacion', 'contratación',
    'compra', 'compras', 'suministro', 'suministros', 'item', 'items', 'solicitud', 'para',
    'entidad', 'publica', 'distrito', 'provincia', 'departamento', 'ano', 'año'
])

def limpiar_texto_nfd(texto: str) -> str:
    """
    Realiza limpieza con Expresiones Regulares (Regex) y normalización Unicode NFD.
    Remueve diacríticos, caracteres corruptos (ej. ADQUISICI¿N) y normaliza a minúsculas.
    """
    if not isinstance(texto, str) or not texto.strip():
        return ""

    # Normalización NFD para separar acentos de letras
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

    # Convertir a minúsculas
    texto = texto.lower()

    # Reemplazar caracteres no alfanuméricos por espacios
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

    # Reemplazar múltiples espacios consecutivos por un único espacio
    texto = re.sub(r'\s+', ' ', texto).strip()

    # Remover stopwords
    palabras = [p for p in texto.split() if p not in STOPWORDS_ES and len(p) > 2]
    return ' '.join(palabras)

def calcular_matriz_tfidf(descripciones: list, max_features: int = 1000):
    """
    Genera la matriz TF-IDF (n-grams 1 y 2) para una lista de descripciones de ítems.
    """
    descripciones_limpias = [limpiar_texto_nfd(d) for d in descripciones]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=max_features,
        min_df=1
    )
    matriz_tfidf = vectorizer.fit_transform(descripciones_limpias)
    return vectorizer, matriz_tfidf


def matriz_similitud_grupo(descripciones_limpias) -> np.ndarray:
    """Matriz de similitud coseno (diagonal en 0) para textos ya limpios."""
    n = len(descripciones_limpias)
    if n <= 1:
        return np.zeros((n, n))
    try:
        matriz = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(
            descripciones_limpias
        )
        sim = cosine_similarity(matriz)
    except ValueError:
        # Vocabulario vacío (textos sin contenido útil).
        return np.zeros((n, n))
    np.fill_diagonal(sim, 0.0)
    return sim


def calcular_similitud_coseno_maxima(df_convocatorias: pd.DataFrame) -> np.ndarray:
    """
    Máxima similitud de coseno de cada convocatoria con otras de la misma entidad.

    Se conserva por compatibilidad: el motor de reglas ya no la utiliza porque
    ignora la ventana temporal.
    """
    df = df_convocatorias.reset_index(drop=True)
    desc = df['descripcion_item'].apply(limpiar_texto_nfd)
    resultado = np.zeros(len(df))
    for _, idx in df.groupby('entidad_ruc').indices.items():
        if len(idx) > 1:
            sim = matriz_similitud_grupo(desc.iloc[idx].tolist())
            resultado[idx] = sim.max(axis=1)
    return resultado
