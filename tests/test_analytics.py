"""
Tests unitarios para src/analytics.py.

Cobertura:
  calcular_estadisticas()  — retorna DataFrame con estructura esperada.
  etiquetar_riesgo()       — añade columna booleana con umbrales correctos.
  generar_recomendaciones()— retorna strings no vacíos con contenido coherente.
  entrenar_modelo()        — devuelve modelo con método predict.
  predecir_riesgo()        — añade probabilidades en rango [0, 1].
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analytics import (
    UMBRAL_ASISTENCIA,
    UMBRAL_CALIFICACION,
    UMBRAL_ENTREGAS,
    calcular_estadisticas,
    entrenar_modelo,
    etiquetar_riesgo,
    generar_recomendaciones,
    predecir_riesgo,
)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def df_muestra():
    """
    DataFrame de 20 estudiantes sintéticos con distribución realista.
    5 en riesgo por calificación, 15 sin riesgo en calificación.
    """
    np.random.seed(42)
    n = 20
    # Garantizamos estudiantes en riesgo y fuera de riesgo para ML
    cal_final = np.concatenate([
        np.random.uniform(35, 58, 5),   # 5 por debajo del umbral
        np.random.uniform(65, 96, 15),  # 15 por encima
    ])
    return pd.DataFrame({
        "id_estudiante": [f"EST{i:03d}" for i in range(1, n + 1)],
        "nombre": [f"Estudiante{i}" for i in range(1, n + 1)],
        "calificacion_1": np.random.uniform(40, 96, n),
        "calificacion_2": np.random.uniform(40, 96, n),
        "calificacion_final": cal_final,
        "asistencia_pct": np.random.uniform(60, 100, n),
        "participacion_foro": np.random.randint(2, 19, n),
        "entregas_completadas": np.random.randint(3, 10, n),
    })


# ── calcular_estadisticas ─────────────────────────────────────────────────────

class TestEstadisticas:

    def test_retorna_dataframe(self, df_muestra):
        assert isinstance(calcular_estadisticas(df_muestra), pd.DataFrame)

    def test_contiene_columna_calificacion_final(self, df_muestra):
        resultado = calcular_estadisticas(df_muestra)
        assert "calificacion_final" in resultado.columns

    def test_contiene_fila_mean(self, df_muestra):
        resultado = calcular_estadisticas(df_muestra)
        assert "mean" in resultado.index

    def test_contiene_fila_std(self, df_muestra):
        resultado = calcular_estadisticas(df_muestra)
        assert "std" in resultado.index

    def test_valores_numericos(self, df_muestra):
        """Todos los valores del resultado deben ser numéricos."""
        resultado = calcular_estadisticas(df_muestra)
        assert resultado.dtypes.apply(lambda d: np.issubdtype(d, np.number)).all()


# ── etiquetar_riesgo ──────────────────────────────────────────────────────────

class TestEtiquetarRiesgo:

    def test_agrega_columna_en_riesgo(self, df_muestra):
        resultado = etiquetar_riesgo(df_muestra)
        assert "en_riesgo" in resultado.columns

    def test_columna_es_booleana(self, df_muestra):
        resultado = etiquetar_riesgo(df_muestra)
        assert resultado["en_riesgo"].dtype == bool

    def test_no_modifica_dataframe_original(self, df_muestra):
        """La función debe operar sobre una copia."""
        etiquetar_riesgo(df_muestra)
        assert "en_riesgo" not in df_muestra.columns

    def test_calificacion_baja_activa_riesgo(self):
        """calificacion_final justo por debajo del umbral → en_riesgo = True."""
        df = pd.DataFrame([{
            "id_estudiante": "EST001", "nombre": "X",
            "calificacion_1": 70, "calificacion_2": 70,
            "calificacion_final": UMBRAL_CALIFICACION - 0.1,
            "asistencia_pct": 90, "participacion_foro": 10, "entregas_completadas": 8,
        }])
        # pandas retorna np.True_, usamos == en lugar de `is`
        assert etiquetar_riesgo(df).iloc[0]["en_riesgo"] == True  # noqa: E712

    def test_asistencia_baja_activa_riesgo(self):
        """asistencia_pct por debajo del umbral → en_riesgo = True (aunque la nota sea buena)."""
        df = pd.DataFrame([{
            "id_estudiante": "EST002", "nombre": "X",
            "calificacion_1": 85, "calificacion_2": 85,
            "calificacion_final": 85,
            "asistencia_pct": UMBRAL_ASISTENCIA - 0.1,
            "participacion_foro": 10, "entregas_completadas": 8,
        }])
        assert etiquetar_riesgo(df).iloc[0]["en_riesgo"] == True  # noqa: E712

    def test_entregas_bajas_activan_riesgo(self):
        """entregas_completadas por debajo del umbral → en_riesgo = True."""
        df = pd.DataFrame([{
            "id_estudiante": "EST003", "nombre": "X",
            "calificacion_1": 85, "calificacion_2": 85,
            "calificacion_final": 85, "asistencia_pct": 90,
            "participacion_foro": 10,
            "entregas_completadas": UMBRAL_ENTREGAS - 1,
        }])
        assert etiquetar_riesgo(df).iloc[0]["en_riesgo"] == True  # noqa: E712

    def test_estudiante_excelente_no_es_riesgo(self):
        """Un estudiante con todas las métricas por encima de los umbrales → False."""
        df = pd.DataFrame([{
            "id_estudiante": "EST004", "nombre": "X",
            "calificacion_1": 95, "calificacion_2": 92,
            "calificacion_final": 94, "asistencia_pct": 98,
            "participacion_foro": 15, "entregas_completadas": 10,
        }])
        assert etiquetar_riesgo(df).iloc[0]["en_riesgo"] == False  # noqa: E712


# ── generar_recomendaciones ───────────────────────────────────────────────────

class TestRecomendaciones:

    def test_retorna_string(self, df_muestra):
        df = etiquetar_riesgo(df_muestra)
        assert isinstance(generar_recomendaciones(df.iloc[0]), str)

    def test_string_no_vacio(self, df_muestra):
        """Todos los estudiantes deben recibir al menos una recomendación."""
        df = etiquetar_riesgo(df_muestra)
        for _, fila in df.iterrows():
            assert len(generar_recomendaciones(fila)) > 0

    def test_estudiante_excelente_recomendacion_positiva(self):
        """Un estudiante sin problemas debe recibir una recomendación positiva."""
        fila = pd.Series({
            "calificacion_final": 95,
            "asistencia_pct": 98,
            "participacion_foro": 15,
            "entregas_completadas": 10,
        })
        rec = generar_recomendaciones(fila)
        assert "[OK]" in rec or "satisfactorio" in rec.lower()

    def test_estudiante_critico_menciona_tutoria(self):
        """Un estudiante con calificación crítica debe recibir sugerencia de tutoría."""
        fila = pd.Series({
            "calificacion_final": UMBRAL_CALIFICACION - 10,
            "asistencia_pct": 50,
            "participacion_foro": 2,
            "entregas_completadas": 2,
        })
        rec = generar_recomendaciones(fila)
        assert "tutoría" in rec.lower() or "[CRITICO]" in rec


# ── Machine Learning ──────────────────────────────────────────────────────────

class TestML:

    def test_modelo_tiene_predict(self, df_muestra):
        """El modelo entrenado debe exponer el método predict."""
        df = etiquetar_riesgo(df_muestra)
        modelo, scaler, _, _, _ = entrenar_modelo(df)
        assert hasattr(modelo, "predict")

    def test_predecir_agrega_columna(self, df_muestra):
        """predecir_riesgo debe añadir la columna 'prob_riesgo_ml'."""
        df = etiquetar_riesgo(df_muestra)
        modelo, scaler, _, _, _ = entrenar_modelo(df)
        df_pred = predecir_riesgo(df, modelo, scaler)
        assert "prob_riesgo_ml" in df_pred.columns

    def test_probabilidades_entre_0_y_1(self, df_muestra):
        """Las probabilidades de riesgo deben estar en el rango [0, 1]."""
        df = etiquetar_riesgo(df_muestra)
        modelo, scaler, _, _, _ = entrenar_modelo(df)
        df_pred = predecir_riesgo(df, modelo, scaler)
        assert df_pred["prob_riesgo_ml"].between(0, 1).all()

    def test_longitud_predicciones_igual_dataset(self, df_muestra):
        """El número de predicciones debe coincidir con el número de filas."""
        df = etiquetar_riesgo(df_muestra)
        modelo, scaler, _, _, _ = entrenar_modelo(df)
        df_pred = predecir_riesgo(df, modelo, scaler)
        assert len(df_pred) == len(df_muestra)

    def test_no_modifica_df_original(self, df_muestra):
        """predecir_riesgo no debe modificar el DataFrame de entrada."""
        df = etiquetar_riesgo(df_muestra)
        modelo, scaler, _, _, _ = entrenar_modelo(df)
        predecir_riesgo(df, modelo, scaler)
        assert "prob_riesgo_ml" not in df.columns
