"""
Blockchain simplificada para registros educativos.

Cada bloque guarda el hash SHA-256 del bloque anterior. Si alguien modifica
un dato, su hash cambia pero el siguiente bloque sigue apuntando al hash
viejo, rompiendo la cadena y haciendo la alteracion detectable.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Bloque:
    indice: int
    timestamp: float
    datos: dict
    hash_previo: str
    hash_propio: str = field(default="", init=False)
    firma: Optional[bytes] = field(default=None)

    def calcular_hash(self) -> str:
        contenido = json.dumps(
            {
                "indice": self.indice,
                "timestamp": self.timestamp,
                "datos": self.datos,
                "hash_previo": self.hash_previo,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()

    def __post_init__(self):
        self.hash_propio = self.calcular_hash()

    def es_valido(self) -> bool:
        return self.hash_propio == self.calcular_hash()

    def __repr__(self):
        return f"Bloque(idx={self.indice}, hash={self.hash_propio[:14]}...)"


class Blockchain:
    HASH_GENESIS = "0" * 64

    def __init__(self):
        self.cadena: list[Bloque] = []
        self._crear_bloque_genesis()

    def _crear_bloque_genesis(self):
        genesis = Bloque(
            indice=0,
            timestamp=time.time(),
            datos={
                "tipo": "genesis",
                "sistema": "LA-Crypto v1.0",
                "descripcion": "Bloque inicial - registro de datos educativos protegidos",
            },
            hash_previo=self.HASH_GENESIS,
        )
        self.cadena.append(genesis)

    def agregar_bloque(self, datos: dict, clave_privada=None) -> Bloque:
        """Crea un bloque nuevo enlazado al ultimo de la cadena."""
        anterior = self.cadena[-1]
        nuevo = Bloque(
            indice=len(self.cadena),
            timestamp=time.time(),
            datos=datos,
            hash_previo=anterior.hash_propio,
        )
        if clave_privada is not None:
            from src.crypto_utils import firmar as _firmar
            nuevo.firma = _firmar(nuevo.hash_propio.encode("utf-8"), clave_privada)
        self.cadena.append(nuevo)
        return nuevo

    def verificar_integridad(self, clave_publica=None) -> bool:
        """
        Recorre la cadena verificando que:
        1. El hash almacenado coincide con el recalculado.
        2. El hash_previo apunta correctamente al bloque anterior.
        3. La firma RSA es valida (si se proporciona clave_publica).
        """
        print(f"\n[BLOCKCHAIN] Verificando {len(self.cadena)} bloques...")

        for i in range(1, len(self.cadena)):
            actual = self.cadena[i]
            anterior = self.cadena[i - 1]

            if actual.hash_propio != actual.calcular_hash():
                print(f"  [FALLO] Bloque {i}: hash_propio no coincide con el recalculado.")
                return False

            if actual.hash_previo != anterior.hash_propio:
                print(f"  [FALLO] Bloque {i}: enlace con bloque {i - 1} roto.")
                return False

            if clave_publica is not None and actual.firma is not None:
                from src.crypto_utils import verificar_firma as _verificar
                if not _verificar(actual.hash_propio.encode("utf-8"), actual.firma, clave_publica):
                    print(f"  [FALLO] Bloque {i}: firma RSA invalida.")
                    return False

        print(f"  [OK] Cadena integra: {len(self.cadena)} bloques verificados.")
        return True

    def imprimir_resumen(self):
        sep = "-" * 70
        print(f"\n{sep}")
        print(f"  BLOCKCHAIN  -  {len(self.cadena)} bloques")
        print(sep)
        for b in self.cadena:
            firmado = "firmado" if b.firma else "sin firma"
            print(f"  [{b.indice:02d}]  hash={b.hash_propio[:16]}...  prev={b.hash_previo[:16]}...  {firmado}")
        print(f"{sep}\n")

    def __len__(self):
        return len(self.cadena)

    def __repr__(self):
        return f"Blockchain({len(self.cadena)} bloques)"
