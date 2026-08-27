"""Hashing de contraseñas y tokens JWT."""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def _create_token(subject: str, minutes: int, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def create_access_token(user_id: int) -> str:
    return _create_token(str(user_id), settings.ACCESS_TOKEN_MINUTES, "access")


def create_refresh_token(user_id: int) -> str:
    return _create_token(str(user_id), settings.REFRESH_TOKEN_DAYS * 24 * 60, "refresh")


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload
