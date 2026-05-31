# Learning Analytics + Criptografía + Blockchain

Sistema académico en Python que protege registros educativos combinando:

- **Learning Analytics** — estadísticas descriptivas, correlaciones y predicción de riesgo con ML.
- **AES (Fernet)** — cifrado simétrico de datos sensibles (nombres, calificaciones).
- **RSA-PSS** — firma digital de cada bloque para garantizar autenticidad del origen.
- **Blockchain simulada** — cadena de hashes SHA-256 que detecta cualquier alteración.

---

## Estructura del proyecto

```
learning-analytics-crypto/
├── data/
│   └── estudiantes.csv       # 30 estudiantes de ejemplo
├── src/
│   ├── __init__.py
│   ├── data_loader.py        # Carga, validación y anonimización de datos
│   ├── crypto_utils.py       # Cifrado AES + firma RSA + gestión de claves
│   ├── blockchain.py         # Cadena de bloques con hashes SHA-256
│   ├── analytics.py          # Estadísticas, indicador de riesgo y ML
│   ├── visualization.py      # Gráficos matplotlib → output/
│   └── main.py               # Orquestador del flujo completo
├── tests/
│   ├── test_crypto.py
│   ├── test_blockchain.py
│   └── test_analytics.py
├── output/                   # Imágenes PNG generadas (se crea automáticamente)
├── keys/                     # Claves criptográficas (excluido del repositorio)
├── app.py                    # Interfaz Streamlit (opcional)
├── conftest.py               # Configuración global de pytest
├── requirements.txt
└── README.md
```

---

## Instalación

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt
```

> **Nota sobre las claves criptográficas:** la carpeta `keys/` no está en el repositorio (excluida por `.gitignore`). Al ejecutar `main.py` por primera vez, el sistema genera automáticamente las claves AES y RSA en esa carpeta. No es necesario ningún paso adicional.

---

## Uso

### Ejecución completa por línea de comandos

```bash
# Desde la raíz del proyecto
python -m src.main

# Con un CSV personalizado
python -m src.main --csv ruta/a/mi_archivo.csv

# Forzar regeneración de claves
python -m src.main --nuevas-claves
```

El script ejecuta 10 pasos y finaliza con un resumen en consola:
```
RESUMEN FINAL
  Estudiantes analizados:   30
  En riesgo (reglas):       10 (33%)
  Calificacion media:       72.0
  Bloques en blockchain:    31
  Integridad blockchain:    INTEGRA
  Alteracion detectada:     Detectada (correcto)
  Graficos generados:       3
```

### Interfaz Streamlit (opcional)

```bash
streamlit run app.py
```

Abre el navegador en `http://localhost:8501`. Permite cargar un CSV, ver
el análisis completo y verificar la blockchain desde la interfaz.

### Tests

```bash
# Ejecutar todos los tests
pytest

# Con detalle de cada test
pytest -v

# Solo un módulo
pytest tests/test_crypto.py -v
```

---

## Decisiones técnicas

### ¿Por qué AES para datos y RSA solo para firmas?

**AES (cifrado simétrico):**
- Una sola clave cifra y descifra.
- Velocidad: ~100x más rápido que RSA para el mismo volumen de datos.
- Fernet = AES-128-CBC + HMAC-SHA256: garantiza confidencialidad e integridad en un solo paso.
- Ideal para cifrar los campos de todos los estudiantes en masa.

**RSA (cifrado asimétrico):**
- Par de claves: privada para firmar, pública para verificar.
- Mucho más lento que AES para datos grandes.
- Se usa **solo para firmas digitales** de cada bloque (firmar el hash, no los datos).
- Garantiza autenticidad: solo quien posee la clave privada pudo crear la firma.

**Patrón híbrido:** cifrar datos masivos con AES (eficiencia) y usar RSA solo para autenticar el origen de cada bloque (seguridad sin penalidad de rendimiento).

---

### ¿Cómo garantiza la cadena de hashes la inmutabilidad?

Cada bloque almacena el hash SHA-256 del bloque anterior:

```
Bloque 0 (génesis)  →  hash_0 = SHA256(contenido_0)
Bloque 1            →  hash_1 = SHA256(contenido_1 + hash_0)
Bloque 2            →  hash_2 = SHA256(contenido_2 + hash_1)
```

Si un atacante modifica los datos del Bloque 1:
1. El hash recalculado del Bloque 1 ≠ hash almacenado → detección inmediata.
2. El Bloque 2 guarda el hash viejo del Bloque 1 → enlace roto → detección al verificar.

Para falsificar la cadena habría que recalcular **todos los hashes desde el bloque alterado hasta el final**, algo que `verificar_integridad()` detecta en milisegundos comparando cada hash almacenado con el recalculado.

---

### Privacidad y ética (GDPR simulado)

| Medida | Implementación |
|---|---|
| **Anonimización** | Nombres reemplazados por `SHA-256(salt + nombre)[:12]` antes de cualquier análisis |
| **Cifrado de datos personales** | Nombre y calificaciones cifrados con AES; solo el poseedor de la clave AES puede descifrarlos |
| **Separación de datos** | El id_estudiante y métricas agregadas se guardan en claro; los campos identificables se cifran |
| **Gestión de claves** | Claves en `keys/` excluido del repositorio; en producción usar HSM o gestor de secretos |
| **No exponer claves** | Las claves nunca aparecen en código fuente; se generan dinámicamente y se leen de archivo |

---

### Modelo de ML — ¿Por qué Regresión Logística?

- **Interpretable:** los coeficientes indican directamente qué variable predice más el riesgo.
- **Adecuada para datasets pequeños:** funciona bien con las ~24 muestras de entrenamiento disponibles.
- **Produce probabilidades:** devuelve `prob_riesgo_ml ∈ [0, 1]`, no solo etiquetas binarias, lo que permite priorizar intervenciones.
- **Baseline sólido:** es el punto de partida estándar en clasificación binaria antes de explorar modelos más complejos.

Features usadas: `calificacion_1`, `calificacion_2`, `asistencia_pct`, `participacion_foro`, `entregas_completadas`.

---

### Limitaciones y mejoras futuras

| Limitación | Mejora futura |
|---|---|
| Blockchain en memoria (se pierde al cerrar) | Persistencia en SQLite o archivo JSON/pickle |
| Sin proof-of-work | Añadir dificultad de minado para resistir reescritura de la cadena |
| Clave AES única para todos los registros | Clave por estudiante con esquema de sobre cifrado |
| 30 estudiantes (ML poco confiable) | Dataset real con cientos de registros; explorar Random Forest o XGBoost |
| Blockchain privada centralizada | Integración con Ethereum/Hyperledger para descentralización real |
| Clave privada RSA sin contraseña | Proteger con passphrase o almacenar en HSM |
| Sin control de acceso | Añadir autenticación de usuarios con roles (admin, docente, estudiante) |

---

## Formato del CSV

El CSV debe contener exactamente estas columnas (en cualquier orden):

| Columna | Tipo | Descripción |
|---|---|---|
| `id_estudiante` | string | Identificador único (ej: `EST001`) |
| `nombre` | string | Nombre completo (será anonimizado) |
| `calificacion_1` | float [0-100] | Primera calificación parcial |
| `calificacion_2` | float [0-100] | Segunda calificación parcial |
| `calificacion_final` | float [0-100] | Calificación final del curso |
| `asistencia_pct` | float [0-100] | Porcentaje de asistencia |
| `participacion_foro` | int | Número de participaciones en foro |
| `entregas_completadas` | int | Número de tareas entregadas |

Los umbrales de riesgo por defecto son:
- `calificacion_final < 60`
- `asistencia_pct < 70`
- `entregas_completadas < 5`

---

## Dependencias principales

| Librería | Versión | Uso |
|---|---|---|
| `pandas` | 3.0.3 | Manipulación de datos tabulares |
| `numpy` | 2.4.6 | Operaciones numéricas |
| `cryptography` | 48.0.0 | AES (Fernet) y RSA |
| `scikit-learn` | 1.8.0 | Regresión Logística, métricas |
| `matplotlib` | 3.10.9 | Visualizaciones |
| `pytest` | 9.0.3 | Tests unitarios |
| `streamlit` | 1.58.0 | Interfaz web |
