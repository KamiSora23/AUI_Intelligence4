"""Persistencia y activación del modelo supervisado (archivo + tabla modelos_ia)."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import text

from modulos_ia.aprendizaje_supervisado import (
    NOMBRE_MODELO,
    VARIABLES,
    Validacion,
    casos_de_referencia,
    entrenar,
)

CARPETA_MODELOS = Path(__file__).resolve().parents[1] / "modelos_entrenados"
MODELO_BASE = "Isolation Forest%"


def _ruta(id_modelo: int) -> Path:
    return CARPETA_MODELOS / f"modelo_supervisado_{int(id_modelo)}.joblib"


def cargar_casos(engine) -> pd.DataFrame:
    """Casos de referencia de todos los lotes (etiquetas y dictámenes)."""
    columnas = ", ".join(f"r.{c}" for c in VARIABLES if c != "monto_referencial")
    with engine.connect() as conn:
        filas = pd.read_sql(
            text(
                f"""
                SELECT r.id_resultado, c.entidad_ruc, c.descripcion_item, c.codigo_cubso,
                       c.monto_referencial, c.fecha_convocatoria, r.estado_revision,
                       r.id_usuario_auditor, r.etiqueta_referencia, r.bono_ia, {columnas}
                FROM resultados_anomalias r
                JOIN convocatorias_procesadas c ON c.id_convocatoria = r.id_convocatoria
                WHERE r.etiqueta_referencia IS NOT NULL
                   OR (r.id_usuario_auditor IS NOT NULL
                       AND r.estado_revision IN ('Confirmado_Fraccionamiento', 'Descartado'))
                """
            ),
            conn,
        )
    return casos_de_referencia(filas)


def _desactivar_todos(conn) -> None:
    conn.execute(
        text("UPDATE modelos_ia SET estado_activo = 0 WHERE nombre_modelo LIKE :n"),
        {"n": f"{NOMBRE_MODELO}%"},
    )
    conn.execute(
        text("UPDATE modelos_ia SET estado_activo = 1 WHERE nombre_modelo LIKE :n"),
        {"n": MODELO_BASE},
    )


def modelo_activo(engine) -> tuple[int, object] | None:
    """Modelo supervisado activo o ``None``.

    Si la base lo marca activo pero falta su archivo, se vuelve al puntaje
    actual en lugar de fallar o de etiquetar resultados con un modelo ausente.
    """
    with engine.begin() as conn:
        id_modelo = conn.execute(
            text(
                "SELECT id_modelo FROM modelos_ia WHERE estado_activo = 1 "
                "AND nombre_modelo LIKE :n ORDER BY id_modelo DESC LIMIT 1"
            ),
            {"n": f"{NOMBRE_MODELO}%"},
        ).scalar()
        if id_modelo is None:
            return None
        if not _ruta(id_modelo).exists():
            _desactivar_todos(conn)
            return None
    return int(id_modelo), joblib.load(_ruta(id_modelo))


def activar(engine, casos: pd.DataFrame, validacion: Validacion) -> int:
    """Entrena con todos los casos y lo deja como modelo activo."""
    if not validacion.supera:
        raise ValueError("El modelo no superó la validación; no se puede activar.")
    modelo = entrenar(casos)
    CARPETA_MODELOS.mkdir(exist_ok=True)
    with engine.begin() as conn:
        id_modelo = conn.execute(
            text(
                """
                INSERT INTO modelos_ia
                    (nombre_modelo, metrica_recall, metrica_roc_auc, estado_activo)
                VALUES (:nombre, :recall, :auc, 0)
                """
            ),
            {
                "nombre": (
                    f"{NOMBRE_MODELO} ({validacion.positivos + validacion.negativos} casos, "
                    f"{validacion.entidades} entidades)"
                ),
                "recall": round(validacion.modelo["sensibilidad"], 4),
                "auc": round(validacion.modelo["roc_auc"], 4),
            },
        ).lastrowid
        # El archivo se escribe dentro de la transacción: si falla, no queda
        # un registro activo sin modelo.
        joblib.dump(modelo, _ruta(id_modelo))
        conn.execute(text("UPDATE modelos_ia SET estado_activo = 0"))
        conn.execute(
            text("UPDATE modelos_ia SET estado_activo = 1 WHERE id_modelo = :i"),
            {"i": id_modelo},
        )
    return int(id_modelo)


def desactivar(engine) -> None:
    """Vuelve al puntaje de reglas + ajuste estadístico."""
    with engine.begin() as conn:
        _desactivar_todos(conn)
