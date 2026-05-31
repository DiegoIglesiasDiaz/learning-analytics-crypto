"""Analisis estadistico y prediccion de riesgo academico."""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


# Umbrales para el indicador de riesgo basado en reglas
UMBRAL_CALIFICACION = 60.0
UMBRAL_ASISTENCIA = 70.0
UMBRAL_ENTREGAS = 5

FEATURES_ML = [
    "calificacion_1", "calificacion_2", "asistencia_pct",
    "participacion_foro", "entregas_completadas",
]


def calcular_estadisticas(df: pd.DataFrame) -> pd.DataFrame:
    columnas = [
        "calificacion_1", "calificacion_2", "calificacion_final",
        "asistencia_pct", "participacion_foro", "entregas_completadas",
    ]
    return df[columnas].agg(["mean", "median", "std", "min", "max"]).round(2)


def calcular_correlaciones(df: pd.DataFrame) -> pd.DataFrame:
    columnas = [
        "calificacion_1", "calificacion_2", "calificacion_final",
        "asistencia_pct", "participacion_foro", "entregas_completadas",
    ]
    return df[columnas].corr().round(3)


def etiquetar_riesgo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columna 'en_riesgo' usando criterio OR sobre tres condiciones.
    Se prefiere identificar de mas (falso positivo) antes que no detectar
    a alguien que necesita intervencion.
    """
    df = df.copy()
    df["en_riesgo"] = (
        (df["calificacion_final"] < UMBRAL_CALIFICACION)
        | (df["asistencia_pct"] < UMBRAL_ASISTENCIA)
        | (df["entregas_completadas"] < UMBRAL_ENTREGAS)
    )
    print(f"[ANALISIS] Estudiantes en riesgo: {df['en_riesgo'].sum()}/{len(df)}")
    return df


def generar_recomendaciones(fila: pd.Series) -> str:
    recs = []

    if fila["calificacion_final"] < UMBRAL_CALIFICACION:
        recs.append("[CRITICO] Calificacion critica - se recomienda tutoria personalizada y revision de contenidos fundamentales.")
    elif fila["calificacion_final"] < 75:
        recs.append("[REFUERZO] Calificacion por debajo del promedio - se sugiere refuerzo con ejercicios adicionales y grupos de estudio.")

    if fila["asistencia_pct"] < UMBRAL_ASISTENCIA:
        recs.append("[ASISTENCIA] Asistencia baja - contactar al estudiante para identificar barreras y ofrecer modalidad flexible.")

    if fila["participacion_foro"] < 5:
        recs.append("[PARTICIPACION] Baja participacion en foros - asignar temas especificos y reconocer aportes.")

    if fila["entregas_completadas"] < UMBRAL_ENTREGAS:
        recs.append("[ENTREGAS] Entregas incompletas - implementar seguimiento semanal y dividir tareas en hitos.")

    if not recs:
        recs.append("[OK] Desempeno satisfactorio - mantener ritmo y considerar actividades de enriquecimiento.")

    return " | ".join(recs)


def entrenar_modelo(df: pd.DataFrame) -> tuple:
    """
    Entrena Regresion Logistica para predecir riesgo academico.
    Se eligio por ser interpretable y funcionar bien con datasets pequenos.
    StandardScaler es necesario porque la RegLog es sensible a la escala.
    """
    if "en_riesgo" not in df.columns:
        df = etiquetar_riesgo(df)

    X = df[FEATURES_ML].values
    y = df["en_riesgo"].astype(int).values

    conteo = np.bincount(y)
    puede_estratificar = len(conteo) >= 2 and conteo.min() >= 2
    solo_train = len(X) < 5 or max(1, int(len(X) * 0.2)) < 2

    if solo_train:
        print("[ML] Dataset muy pequeno - entrenando con todos los datos.")
        scaler = StandardScaler()
        X_sc = scaler.fit_transform(X)
        modelo = LogisticRegression(random_state=42, max_iter=1000)
        modelo.fit(X_sc, y)
        return modelo, scaler, X_sc, y, modelo.predict(X_sc)

    if not puede_estratificar:
        print("[ML] Clases con pocos miembros - split sin estratificacion.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=y if puede_estratificar else None,
    )

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    modelo = LogisticRegression(random_state=42, max_iter=1000)
    modelo.fit(X_train_sc, y_train)
    y_pred = modelo.predict(X_test_sc)

    print(f"\n[ML] Accuracy: {accuracy_score(y_test, y_pred):.2%}")
    print(f"[ML] Confusion matrix:\n{confusion_matrix(y_test, y_pred)}")
    print(f"[ML] Reporte:\n{classification_report(y_test, y_pred, zero_division=0)}")

    return modelo, scaler, X_test, y_test, y_pred


def predecir_riesgo(df: pd.DataFrame, modelo, scaler) -> pd.DataFrame:
    """Agrega columna prob_riesgo_ml con la probabilidad de riesgo (0 a 1)."""
    df = df.copy()
    X_sc = scaler.transform(df[FEATURES_ML].values)
    df["prob_riesgo_ml"] = modelo.predict_proba(X_sc)[:, 1]
    return df
