"""Graficos de learning analytics guardados como PNG en output/."""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DIRECTORIO_SALIDA = Path("output")

AZUL = "#2196F3"
ROJO = "#E53935"
VERDE = "#43A047"
NARANJA = "#FB8C00"
GRIS = "#9E9E9E"


def _guardar(nombre: str) -> str:
    DIRECTORIO_SALIDA.mkdir(exist_ok=True)
    ruta = DIRECTORIO_SALIDA / nombre
    plt.tight_layout()
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[VIZ] Guardado: {ruta}")
    return str(ruta)


def histograma_calificaciones(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.hist(df["calificacion_final"], bins=10, range=(0, 100),
            color=AZUL, edgecolor="white", alpha=0.85)
    ax.axvspan(0, 60, alpha=0.10, color=ROJO)
    ax.axvline(60, color=ROJO, linestyle="--", linewidth=1.8, label="Umbral riesgo (60)")
    media = df["calificacion_final"].mean()
    ax.axvline(media, color=NARANJA, linewidth=2.0, label=f"Media: {media:.1f}")

    ax.set_title("Distribucion de Calificaciones Finales", fontsize=14, fontweight="bold")
    ax.set_xlabel("Calificacion Final (0-100)", fontsize=12)
    ax.set_ylabel("Numero de estudiantes", fontsize=12)
    ax.set_xlim(0, 100)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    return _guardar("histograma_calificaciones.png")


def dispersion_asistencia_calificacion(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 6))

    if "en_riesgo" in df.columns:
        colores = df["en_riesgo"].map({True: ROJO, False: VERDE}).tolist()
        ax.legend(handles=[
            mpatches.Patch(color=VERDE, label="Sin riesgo"),
            mpatches.Patch(color=ROJO, label="En riesgo"),
        ])
    else:
        colores = AZUL

    ax.scatter(df["asistencia_pct"], df["calificacion_final"],
               c=colores, alpha=0.78, s=85, edgecolors="white", linewidth=0.6)

    z = np.polyfit(df["asistencia_pct"], df["calificacion_final"], 1)
    x_line = np.linspace(df["asistencia_pct"].min(), df["asistencia_pct"].max(), 100)
    ax.plot(x_line, np.poly1d(z)(x_line), "--", color=GRIS, linewidth=1.5, label="Tendencia")

    ax.axhline(60, color=ROJO, linestyle=":", alpha=0.5)
    ax.axvline(70, color=NARANJA, linestyle=":", alpha=0.5)

    ax.set_title("Asistencia vs. Calificacion Final", fontsize=14, fontweight="bold")
    ax.set_xlabel("Asistencia (%)", fontsize=12)
    ax.set_ylabel("Calificacion Final", fontsize=12)
    ax.set_xlim(40, 105)
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.25)
    return _guardar("dispersion_asistencia.png")


def barras_estudiantes_riesgo(df: pd.DataFrame) -> str:
    if "en_riesgo" not in df.columns:
        raise ValueError("El DataFrame necesita la columna 'en_riesgo'.")

    df_ord = df.sort_values("calificacion_final", ascending=True).copy()
    etiqueta = "nombre_anonimo" if "nombre_anonimo" in df.columns else "id_estudiante"
    colores = df_ord["en_riesgo"].map({True: ROJO, False: VERDE}).tolist()

    fig, ax = plt.subplots(figsize=(10, max(6, len(df_ord) * 0.38)))
    ax.barh(df_ord[etiqueta], df_ord["calificacion_final"],
            color=colores, edgecolor="white", height=0.70)
    ax.axvline(60, color=ROJO, linestyle="--", linewidth=1.8)

    ax.set_title("Calificacion Final por Estudiante", fontsize=14, fontweight="bold")
    ax.set_xlabel("Calificacion Final (0-100)", fontsize=12)
    ax.set_xlim(0, 115)
    ax.grid(axis="x", alpha=0.25)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(handles=[
        mpatches.Patch(color=ROJO, label="En riesgo"),
        mpatches.Patch(color=VERDE, label="Sin riesgo"),
        plt.Line2D([0], [0], color=ROJO, linestyle="--", label="Umbral (60)"),
    ])
    return _guardar("barras_estudiantes.png")


def generar_todas_las_visualizaciones(df: pd.DataFrame) -> list[str]:
    rutas = [histograma_calificaciones(df), dispersion_asistencia_calificacion(df)]
    if "en_riesgo" in df.columns:
        rutas.append(barras_estudiantes_riesgo(df))
    return rutas
