"""Carga, validacion y anonimizacion de datos de estudiantes."""

import hashlib
import os
import pandas as pd


COLUMNAS_REQUERIDAS = [
    "id_estudiante", "nombre", "calificacion_1", "calificacion_2",
    "calificacion_final", "asistencia_pct", "participacion_foro",
    "entregas_completadas",
]

COLUMNAS_NUMERICAS = [
    "calificacion_1", "calificacion_2", "calificacion_final",
    "asistencia_pct", "participacion_foro", "entregas_completadas",
]


def cargar_datos(ruta_csv: str) -> pd.DataFrame:
    """Carga el CSV, valida columnas requeridas e imputa valores nulos."""
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_csv}")

    try:
        df = pd.read_csv(ruta_csv)
    except Exception as exc:
        raise ValueError(f"Error al leer el CSV: {exc}") from exc

    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes: {faltantes}")

    # Nulos numericos -> mediana de cada columna
    for col in COLUMNAS_NUMERICAS:
        if df[col].isnull().any():
            mediana = df[col].median()
            df[col] = df[col].fillna(mediana)
            print(f"  [AVISO] '{col}' imputada con mediana ({mediana:.1f})")

    df["nombre"] = df["nombre"].fillna("Desconocido")

    for col in COLUMNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"[OK] {len(df)} estudiantes cargados.")
    return df


def anonimizar_nombres(
    df: pd.DataFrame,
    salt: str = "edu_salt_2024",
    eliminar_original: bool = True,
) -> pd.DataFrame:
    """
    Sustituye cada nombre por un hash SHA-256 truncado (simulacion GDPR).
    El salt dificulta ataques de diccionario sobre nombres comunes.
    Por defecto elimina la columna 'nombre' original del DataFrame.
    """
    def _hash(nombre: str) -> str:
        contenido = f"{salt}:{nombre}".encode("utf-8")
        return "ANON_" + hashlib.sha256(contenido).hexdigest()[:12].upper()

    df = df.copy()
    df["nombre_anonimo"] = df["nombre"].apply(_hash)

    if eliminar_original:
        df = df.drop(columns=["nombre"])
        print("[OK] Nombres anonimizados (columna original eliminada).")
    else:
        print("[OK] Nombres anonimizados.")

    return df
