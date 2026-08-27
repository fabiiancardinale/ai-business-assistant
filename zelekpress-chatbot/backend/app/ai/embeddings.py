"""Embeddings desacoplados.

Por defecto usa un embebedor local determinístico (bag-of-words con hashing)
que NO necesita ninguna API ni dependencias pesadas: sirve para recuperación
por palabras clave y corre en cualquier lado (ideal para dev y tests).

Cuando se quiera máxima calidad semántica, se implementa un adapter con
modelo (OpenAI/others) respetando la misma interfaz `embed()`, y en Postgres
se migran los vectores a pgvector. El resto del sistema no cambia."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

DIM = 256


def _stable_hash(token: str) -> int:
    """Hash determinístico (el hash() nativo de Python es aleatorio por
    proceso, lo que rompería los vectores guardados entre reinicios)."""
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


_token_re = re.compile(r"[a-záéíóúñü0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return _token_re.findall((text or "").lower())


class HashingEmbedder:
    """Vector disperso normalizado por hashing de tokens. Determinístico."""
    def embed(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for tok in _tokens(text):
            vec[_stable_hash(tok) % DIM] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    # a y b vienen normalizados => coseno = producto punto.
    return sum(x * y for x, y in zip(a, b))


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = HashingEmbedder()
    return _embedder
