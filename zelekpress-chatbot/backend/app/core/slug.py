"""Generación de slugs únicos."""
import re
import secrets

_MAP = str.maketrans("áéíóúñüÁÉÍÓÚÑÜ", "aeiounuAEIOUNU")


def slugify(text: str) -> str:
    text = text.translate(_MAP).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "empresa"


def unique_slug(db, model, base: str) -> str:
    """Devuelve un slug único para `model`, agregando sufijo si hace falta."""
    from sqlalchemy import select

    slug = slugify(base)
    candidate = slug
    while db.scalar(select(model).where(model.slug == candidate)):
        candidate = f"{slug}-{secrets.token_hex(3)}"
    return candidate
