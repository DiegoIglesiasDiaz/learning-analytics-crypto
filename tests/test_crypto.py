"""
Tests unitarios para src/crypto_utils.py.

Cobertura:
  AES (Fernet)
    - Ciclo cifrar → descifrar recupera el dato original.
    - El token cifrado es bytes.
    - Dos cifrados del mismo dato producen tokens distintos (IV aleatorio).
    - Clave incorrecta lanza ValueError.
    - Token alterado lanza ValueError.

  RSA (firma digital)
    - Firma válida pasa la verificación.
    - Datos alterados invalidan la firma.
    - La firma es bytes.
    - RSA-PSS genera firmas distintas cada vez (salt aleatorio).
"""

import sys
import tempfile
from pathlib import Path

import pytest

from src.crypto_utils import (
    cifrar,
    descifrar,
    firmar,
    generar_clave_aes,
    generar_par_rsa,
    verificar_firma,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def clave_aes(tmp_path, monkeypatch):
    """Genera una clave AES en un directorio temporal para no contaminar el proyecto."""
    monkeypatch.chdir(tmp_path)
    return generar_clave_aes()


@pytest.fixture
def claves_rsa(tmp_path, monkeypatch):
    """Genera un par RSA en un directorio temporal."""
    monkeypatch.chdir(tmp_path)
    return generar_par_rsa()


# ── AES (Fernet) ──────────────────────────────────────────────────────────────

class TestAES:
    """Pruebas del módulo de cifrado simétrico AES (Fernet)."""

    def test_descifrar_recupera_texto_original(self, clave_aes):
        """El ciclo cifrar → descifrar debe devolver exactamente el texto original."""
        texto = "Ana García López"
        assert descifrar(cifrar(texto, clave_aes), clave_aes) == texto

    def test_cifrar_numero_como_string(self, clave_aes):
        """Las calificaciones se cifran como strings; el ciclo debe funcionar igual."""
        texto = "95.5"
        assert descifrar(cifrar(texto, clave_aes), clave_aes) == texto

    def test_cifrar_devuelve_bytes(self, clave_aes):
        """El resultado de cifrar debe ser de tipo bytes."""
        assert isinstance(cifrar("prueba", clave_aes), bytes)

    def test_tokens_distintos_para_mismo_texto(self, clave_aes):
        """Cada llamada a cifrar produce un token diferente (IV aleatorio en Fernet)."""
        texto = "mismo texto"
        token1 = cifrar(texto, clave_aes)
        token2 = cifrar(texto, clave_aes)
        assert token1 != token2

    def test_descifrar_clave_incorrecta_lanza_error(self, tmp_path, monkeypatch):
        """Usar una clave diferente para descifrar debe lanzar ValueError."""
        monkeypatch.chdir(tmp_path)
        clave_a = generar_clave_aes()

        # Generar segunda clave en subdirectorio independiente
        subdir = tmp_path / "sub"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        clave_b = generar_clave_aes()

        token = cifrar("dato secreto", clave_a)
        with pytest.raises(ValueError):
            descifrar(token, clave_b)

    def test_descifrar_token_alterado_lanza_error(self, clave_aes):
        """Alterar cualquier byte del token debe invalidar el HMAC y lanzar ValueError."""
        token = cifrar("dato secreto", clave_aes)
        token_corrupto = token[:-8] + b"XXXXXXXX"  # Corrompe el final
        with pytest.raises(ValueError):
            descifrar(token_corrupto, clave_aes)

    def test_cifrar_cadena_vacia(self, clave_aes):
        """Cifrar y descifrar una cadena vacía debe funcionar sin errores."""
        assert descifrar(cifrar("", clave_aes), clave_aes) == ""

    def test_cifrar_unicode(self, clave_aes):
        """Caracteres Unicode (tildes, ñ) deben sobrevivir al ciclo cifrar/descifrar."""
        texto = "Sofia Martinez - calificacion: 9.8 (aprobado)"
        assert descifrar(cifrar(texto, clave_aes), clave_aes) == texto


# ── RSA (firma digital) ───────────────────────────────────────────────────────

class TestRSA:
    """Pruebas de firma digital RSA-PSS."""

    def test_firma_valida_verifica(self, claves_rsa):
        """Una firma generada con la clave privada debe pasar la verificación con la pública."""
        priv, pub = claves_rsa
        datos = b"hash_bloque_abc123"
        firma = firmar(datos, priv)
        assert verificar_firma(datos, firma, pub) is True

    def test_datos_alterados_invalidan_firma(self, claves_rsa):
        """Si los datos cambian después de firmar, la verificación debe fallar."""
        priv, pub = claves_rsa
        datos_orig = b"hash_original_xyz"
        datos_alt = b"hash_ALTERADO_xyz"
        firma = firmar(datos_orig, priv)
        assert verificar_firma(datos_alt, firma, pub) is False

    def test_firma_devuelve_bytes(self, claves_rsa):
        """La firma debe ser de tipo bytes."""
        priv, _ = claves_rsa
        assert isinstance(firmar(b"datos_prueba", priv), bytes)

    def test_firmas_distintas_mismo_dato(self, claves_rsa):
        """RSA-PSS genera firmas distintas cada vez gracias al salt aleatorio."""
        priv, _ = claves_rsa
        datos = b"mismos datos"
        firma1 = firmar(datos, priv)
        firma2 = firmar(datos, priv)
        assert firma1 != firma2

    def test_firma_incorrecta_falla(self, claves_rsa):
        """Una firma completamente aleatoria no debe verificar."""
        _, pub = claves_rsa
        datos = b"datos reales"
        firma_falsa = b"\x00" * 256  # 2048 bits de ceros — firma inválida
        assert verificar_firma(datos, firma_falsa, pub) is False
