"""
conftest.py — configuración global de pytest.

Añade la raíz del proyecto al sys.path una sola vez para todos los tests,
evitando repetir sys.path.insert(0, ...) en cada archivo de test.
"""

import sys
from pathlib import Path

# Insertar la raíz del proyecto al inicio del path de importación
sys.path.insert(0, str(Path(__file__).parent))
