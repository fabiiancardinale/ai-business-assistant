"""Subida segura de imágenes (launcher, logo, avatar). Valida el tipo real
por firma de bytes, no solo por la extensión declarada."""
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_SIZE = 2 * 1024 * 1024  # 2 MB

# firma de bytes -> extensión
_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
}


def _detect_ext(head: bytes) -> str | None:
    for sig, ext in _SIGNATURES.items():
        if head.startswith(sig):
            return ext
    # WEBP: 'RIFF'....'WEBP'
    if head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def save_image(file: UploadFile, subdir: str, name: str) -> str:
    """Guarda la imagen y devuelve su ruta pública (/uploads/...)."""
    data = file.file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="La imagen supera los 2 MB")

    ext = _detect_ext(data[:16])
    if not ext:
        raise HTTPException(status_code=400, detail="Formato no válido. Usá PNG, JPG o WEBP.")

    dest_dir = Path(settings.UPLOADS_DIR) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{name}_{secrets.token_hex(4)}{ext}"
    (dest_dir / filename).write_bytes(data)

    # Ruta pública relativa (la sirve StaticFiles en /uploads).
    return f"/uploads/{subdir}/{filename}"
