"""
Cifrado AES (Fernet) y firmas digitales RSA para proteger registros educativos.

Se usa un esquema hibrido: AES cifra los datos porque es rapido (~100x mas
que RSA), y RSA solo firma el hash de cada bloque para autenticar el origen.
Las claves se guardan en keys/ que esta excluido del repositorio (.gitignore).
"""

from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey


DIRECTORIO_CLAVES = Path("keys")


def _init_keys_dir():
    DIRECTORIO_CLAVES.mkdir(exist_ok=True)


def generar_clave_aes() -> bytes:
    _init_keys_dir()
    clave = Fernet.generate_key()
    (DIRECTORIO_CLAVES / "fernet.key").write_bytes(clave)
    print(f"[OK] Clave AES generada -> {DIRECTORIO_CLAVES / 'fernet.key'}")
    return clave


def cargar_clave_aes() -> bytes:
    ruta = DIRECTORIO_CLAVES / "fernet.key"
    if not ruta.exists():
        raise FileNotFoundError("Clave AES no encontrada. Ejecuta generar_clave_aes() primero.")
    return ruta.read_bytes()


def cifrar(dato: str, clave: bytes) -> bytes:
    try:
        return Fernet(clave).encrypt(dato.encode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Error al cifrar: {exc}") from exc


def descifrar(token: bytes, clave: bytes) -> str:
    try:
        return Fernet(clave).decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Token invalido: clave incorrecta o datos alterados.") from exc
    except Exception as exc:
        raise ValueError(f"Error al descifrar: {exc}") from exc


def generar_par_rsa() -> tuple[RSAPrivateKey, RSAPublicKey]:
    """Genera par de claves RSA 2048 bits y las persiste en keys/."""
    _init_keys_dir()
    # 65537 como exponente publico es el estandar por su eficiencia
    clave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    clave_publica = clave_privada.public_key()

    (DIRECTORIO_CLAVES / "rsa_privada.pem").write_bytes(
        clave_privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (DIRECTORIO_CLAVES / "rsa_publica.pem").write_bytes(
        clave_publica.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    print("[OK] Par de claves RSA (2048 bits) generado.")
    return clave_privada, clave_publica


def cargar_claves_rsa() -> tuple[RSAPrivateKey, RSAPublicKey]:
    ruta_priv = DIRECTORIO_CLAVES / "rsa_privada.pem"
    ruta_pub = DIRECTORIO_CLAVES / "rsa_publica.pem"
    if not ruta_priv.exists() or not ruta_pub.exists():
        raise FileNotFoundError("Claves RSA no encontradas. Ejecuta generar_par_rsa() primero.")
    clave_privada = serialization.load_pem_private_key(ruta_priv.read_bytes(), password=None)
    clave_publica = serialization.load_pem_public_key(ruta_pub.read_bytes())
    return clave_privada, clave_publica


def firmar(datos: bytes, clave_privada: RSAPrivateKey) -> bytes:
    """Firma con RSA-PSS. El salt aleatorio hace que cada firma sea unica."""
    return clave_privada.sign(
        datos,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )


def verificar_firma(datos: bytes, firma: bytes, clave_publica: RSAPublicKey) -> bool:
    try:
        clave_publica.verify(
            firma,
            datos,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False
