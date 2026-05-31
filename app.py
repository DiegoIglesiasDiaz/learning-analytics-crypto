"""Interfaz web Streamlit para el sistema Learning Analytics + Blockchain."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.analytics import (
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
    generar_clave_aes,
    generar_par_rsa,
)
from src.data_loader import anonimizar_nombres
from src.main import cifrar_registro
from src.visualization import (
    barras_estudiantes_riesgo,
    dispersion_asistencia_calificacion,
    histograma_calificaciones,
)


st.set_page_config(page_title="LA-Crypto: Learning Analytics + Blockchain", layout="wide")
st.title("LA-Crypto: Learning Analytics + Criptografia + Blockchain")
st.caption("Protege registros educativos con AES (cifrado simetrico), RSA (firma digital) y una blockchain con hashes SHA-256 encadenados.")

with st.sidebar:
    st.header("Configuracion")
    archivo = st.file_uploader("Cargar CSV de estudiantes", type=["csv"])
    usar_anonimizacion = st.checkbox("Anonimizar nombres (GDPR)", value=True)
    usar_ml = st.checkbox("Activar prediccion ML", value=True)
    ejecutar = st.button("Ejecutar analisis", type="primary", use_container_width=True)
    st.divider()
    st.caption("Las claves se guardan en keys/ (excluido del repo). En produccion usar un gestor de secretos.")

if "resultados" not in st.session_state:
    st.session_state.resultados = None

if ejecutar:
    if archivo is None:
        st.warning("Carga un archivo CSV antes de ejecutar.")
    else:
        with st.spinner("Procesando datos..."):
            try:
                df = pd.read_csv(archivo)

                Path("keys").mkdir(exist_ok=True)
                if not (Path("keys") / "fernet.key").exists():
                    clave_aes = generar_clave_aes()
                    clave_priv, clave_pub = generar_par_rsa()
                else:
                    clave_aes = cargar_clave_aes()
                    clave_priv, clave_pub = cargar_claves_rsa()

                # Cifrar nombre real ANTES de anonimizar (mismo orden que main.py)
                bc = Blockchain()
                for _, fila in df.iterrows():
                    bc.agregar_bloque(cifrar_registro(fila, clave_aes), clave_privada=clave_priv)

                if usar_anonimizacion:
                    df = anonimizar_nombres(df)

                df = etiquetar_riesgo(df)
                if usar_ml:
                    modelo, scaler, _, _, _ = entrenar_modelo(df)
                    df = predecir_riesgo(df, modelo, scaler)
                df["recomendacion"] = df.apply(generar_recomendaciones, axis=1)

                st.session_state.resultados = {"df": df, "blockchain": bc, "clave_pub": clave_pub}
                st.success("Analisis completado.")
            except Exception as exc:
                st.error(f"Error durante el analisis: {exc}")

if st.session_state.resultados:
    res = st.session_state.resultados
    df: pd.DataFrame = res["df"]
    bc: Blockchain = res["blockchain"]
    clave_pub = res["clave_pub"]

    tab1, tab2, tab3, tab4 = st.tabs(["Estadisticas", "Visualizaciones", "Blockchain", "Recomendaciones"])

    with tab1:
        st.subheader("Estadisticas Descriptivas")
        st.dataframe(calcular_estadisticas(df), use_container_width=True)

        n_riesgo = int(df["en_riesgo"].sum())
        col1, col2, col3 = st.columns(3)
        col1.metric("En riesgo", n_riesgo, f"{n_riesgo / len(df):.0%}")
        col2.metric("Calificacion media", f"{df['calificacion_final'].mean():.1f}")
        col3.metric("Asistencia media", f"{df['asistencia_pct'].mean():.1f}%")

        cols_mostrar = ["id_estudiante", "calificacion_final", "asistencia_pct",
                        "participacion_foro", "entregas_completadas", "en_riesgo"]
        if "nombre_anonimo" in df.columns:
            cols_mostrar.insert(1, "nombre_anonimo")
        if "prob_riesgo_ml" in df.columns:
            cols_mostrar.append("prob_riesgo_ml")
        st.subheader("Datos completos")
        st.dataframe(df[cols_mostrar], use_container_width=True)

    with tab2:
        st.subheader("Visualizaciones")
        col1, col2 = st.columns(2)
        with col1:
            st.image(histograma_calificaciones(df), caption="Distribucion de calificaciones")
        with col2:
            st.image(dispersion_asistencia_calificacion(df), caption="Asistencia vs. calificacion")
        st.image(barras_estudiantes_riesgo(df), caption="Calificacion por estudiante", use_container_width=True)

    with tab3:
        st.subheader("Verificacion de Integridad")

        if st.button("Verificar integridad de la blockchain"):
            integra = bc.verificar_integridad(clave_publica=clave_pub)
            if integra:
                st.success(f"Blockchain integra: {len(bc)} bloques verificados.")
            else:
                st.error("Integridad comprometida. Se detectaron alteraciones.")

        st.subheader("Explorador de bloques")
        idx = st.slider("Seleccionar bloque", min_value=0, max_value=len(bc) - 1, value=0)
        bloque = bc.cadena[idx]

        col1, col2, col3 = st.columns(3)
        col1.metric("Indice", bloque.indice)
        col2.metric("Firmado (RSA)", "Si" if bloque.firma else "No")
        col3.metric("Valido", "Si" if bloque.es_valido() else "No")

        st.code(f"hash_propio:  {bloque.hash_propio}\nhash_previo:  {bloque.hash_previo}", language="text")
        with st.expander("Datos del bloque (cifrados)"):
            st.json(bloque.datos)

    with tab4:
        st.subheader("Recomendaciones Personalizadas")

        col_id = "nombre_anonimo" if "nombre_anonimo" in df.columns else "id_estudiante"
        sel = st.selectbox("Seleccionar estudiante", df[col_id].tolist())
        fila = df[df[col_id] == sel].iloc[0]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calificacion final", f"{fila['calificacion_final']:.0f}")
        col2.metric("Asistencia", f"{fila['asistencia_pct']:.0f}%")
        col3.metric("Participacion foro", int(fila["participacion_foro"]))
        col4.metric("Entregas", int(fila["entregas_completadas"]))

        if "prob_riesgo_ml" in df.columns:
            st.metric("Probabilidad de riesgo (ML)", f"{fila['prob_riesgo_ml']:.1%}")

        estado = "EN RIESGO" if fila["en_riesgo"] else "SIN RIESGO"
        mensaje = f"**Estado (reglas):** {estado}\n\n{fila['recomendacion']}"

        # Color segun nivel de riesgo: rojo > 60%, naranja 30-60%, verde < 30%
        if "prob_riesgo_ml" in df.columns:
            prob = fila["prob_riesgo_ml"]
            if prob > 0.6:
                st.error(mensaje)
            elif prob > 0.3:
                st.warning(mensaje)
            else:
                st.success(mensaje)
        elif fila["en_riesgo"]:
            st.error(mensaje)
        else:
            st.success(mensaje)

else:
    st.info("**Pasos para comenzar:**\n1. Carga un CSV en el panel lateral.\n2. Ajusta las opciones.\n3. Haz clic en **Ejecutar analisis**.")

    ruta_ejemplo = Path("data/estudiantes.csv")
    if ruta_ejemplo.exists():
        with st.expander("Vista previa del CSV de ejemplo"):
            st.dataframe(pd.read_csv(ruta_ejemplo).head(5))
