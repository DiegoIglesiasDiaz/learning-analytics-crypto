"""
Pipeline principal del sistema Learning Analytics + Criptografia + Blockchain.

Uso:
    python -m src.main
    python -m src.main --csv data/estudiantes.csv --nuevas-claves
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.analytics import (
    calcular_correlaciones,
    calcular_estadisticas,
    entrenar_modelo,
    etiquetar_riesgo,
    generar_recomendaciones,
    predecir_riesgo,
)
from src.blockchain import Blockchain
from src.crypto_utils import (
    cargar_clave_aes,
    cargar_claves_rsa,
    cifrar,
    generar_clave_aes,
    generar_par_rsa,
)
from src.data_loader import anonimizar_nombres, cargar_datos
from src.visualization import generar_todas_las_visualizaciones


def preparar_claves(forzar_nueva: bool = False) -> tuple:
    tiene_aes = (Path("keys") / "fernet.key").exists()
    tiene_rsa = (Path("keys") / "rsa_privada.pem").exists()

    if forzar_nueva or not tiene_aes:
        clave_aes = generar_clave_aes()
    else:
        clave_aes = cargar_clave_aes()
        print("[OK] Clave AES cargada.")

    if forzar_nueva or not tiene_rsa:
        clave_privada, clave_publica = generar_par_rsa()
    else:
        clave_privada, clave_publica = cargar_claves_rsa()
        print("[OK] Claves RSA cargadas.")

    return clave_aes, clave_privada, clave_publica


def cifrar_registro(fila, clave_aes: bytes) -> dict:
    # Nombre y calificaciones cifrados; el resto queda en claro
    # porque no identifica directamente al estudiante
    return {
        "id_estudiante": str(fila["id_estudiante"]),
        "nombre_cifrado": cifrar(str(fila.get("nombre", "N/A")), clave_aes).hex(),
        "cal1_cifrada": cifrar(str(fila["calificacion_1"]), clave_aes).hex(),
        "cal2_cifrada": cifrar(str(fila["calificacion_2"]), clave_aes).hex(),
        "cal_final_cifrada": cifrar(str(fila["calificacion_final"]), clave_aes).hex(),
        "asistencia_pct": float(fila["asistencia_pct"]),
        "participacion_foro": int(fila["participacion_foro"]),
        "entregas_completadas": int(fila["entregas_completadas"]),
    }


def main(ruta_csv: str = "data/estudiantes.csv", forzar_nuevas_claves: bool = False) -> tuple:
    sep = "=" * 65
    print(f"\n{sep}")
    print("   SISTEMA  LEARNING ANALYTICS + CRIPTOGRAFIA + BLOCKCHAIN")
    print(f"{sep}\n")

    print("[PASO 1] Cargando datos educativos...")
    df = cargar_datos(ruta_csv)

    print("\n[PASO 2] Anonimizando nombres (simulacion GDPR)...")
    df = anonimizar_nombres(df)

    print("\n[PASO 3] Preparando claves criptograficas...")
    clave_aes, clave_privada, clave_publica = preparar_claves(forzar_nuevas_claves)

    print("\n[PASO 4] Cifrando registros y registrando en blockchain...")
    blockchain = Blockchain()
    for _, fila in df.iterrows():
        blockchain.agregar_bloque(cifrar_registro(fila, clave_aes), clave_privada=clave_privada)
    print(f"[OK] {len(df)} registros añadidos a la blockchain.")
    blockchain.imprimir_resumen()

    print("[PASO 5] Verificando integridad de la blockchain...")
    integra = blockchain.verificar_integridad(clave_publica=clave_publica)
    estado = "INTEGRA" if integra else "COMPROMETIDA"

    # Demo: modificar un bloque sin recalcular su hash y verificar que se detecta
    print("\n  [DEMO] Simulando alteracion del bloque 2...")
    valor_original = blockchain.cadena[2].datos["asistencia_pct"]
    hash_original = blockchain.cadena[2].hash_propio
    blockchain.cadena[2].datos["asistencia_pct"] = 999
    detectado = not blockchain.verificar_integridad()
    resultado_demo = "Detectada (correcto)" if detectado else "No detectada (error)"
    print(f"  [DEMO] Resultado: alteracion {resultado_demo}")
    blockchain.cadena[2].datos["asistencia_pct"] = valor_original
    blockchain.cadena[2].hash_propio = hash_original

    print("\n[PASO 6] Analisis estadistico...")
    print(f"\n{calcular_estadisticas(df).to_string()}")
    corr = calcular_correlaciones(df)
    print("\n  Correlacion con calificacion_final:")
    print(corr["calificacion_final"].drop("calificacion_final").to_string())

    print("\n[PASO 7] Calculando riesgo y entrenando modelo ML...")
    df = etiquetar_riesgo(df)
    modelo, scaler, _, _, _ = entrenar_modelo(df)
    df = predecir_riesgo(df, modelo, scaler)

    print("\n[PASO 8] Generando recomendaciones personalizadas...")
    df["recomendacion"] = df.apply(generar_recomendaciones, axis=1)

    print("\n  Top 5 estudiantes con mayor probabilidad de riesgo (ML):")
    top5 = df.nlargest(5, "prob_riesgo_ml")[
        ["id_estudiante", "nombre_anonimo", "calificacion_final",
         "asistencia_pct", "prob_riesgo_ml", "recomendacion"]
    ]
    for _, row in top5.iterrows():
        print(f"\n  {row['id_estudiante']} ({row['nombre_anonimo']})")
        print(f"    Cal. final: {row['calificacion_final']:.0f}  |  Asistencia: {row['asistencia_pct']:.0f}%  |  Prob. riesgo ML: {row['prob_riesgo_ml']:.1%}")
        print(f"    Recomendacion: {row['recomendacion'][:120]}...")

    print("\n[PASO 9] Generando visualizaciones...")
    rutas_png = generar_todas_las_visualizaciones(df)
    print(f"[OK] {len(rutas_png)} graficos guardados en output/")

    print(f"\n{sep}")
    print("  RESUMEN FINAL")
    print(sep)
    print(f"  Estudiantes analizados:   {len(df)}")
    print(f"  En riesgo (reglas):       {df['en_riesgo'].sum()} ({df['en_riesgo'].mean():.0%})")
    print(f"  Calificacion media:       {df['calificacion_final'].mean():.1f}")
    print(f"  Asistencia media:         {df['asistencia_pct'].mean():.1f}%")
    print(f"  Bloques en blockchain:    {len(blockchain)}")
    print(f"  Integridad blockchain:    {estado}")
    print(f"  Alteracion detectada:     {resultado_demo}")
    print(f"  Graficos generados:       {len(rutas_png)}")
    print(f"{sep}\n")

    return df, blockchain


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema Learning Analytics + Criptografia + Blockchain")
    parser.add_argument("--csv", default="data/estudiantes.csv", help="Ruta al CSV de estudiantes")
    parser.add_argument("--nuevas-claves", action="store_true", help="Regenerar claves aunque ya existan")
    args = parser.parse_args()
    main(ruta_csv=args.csv, forzar_nuevas_claves=args.nuevas_claves)
