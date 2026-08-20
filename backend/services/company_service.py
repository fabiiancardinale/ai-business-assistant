import secrets
import hashlib

from sqlalchemy.orm import Session

from models import Company


# =========================================================
# CONTRASEÑA DEL PORTAL DE CLIENTES
#
# Hash simple con hashlib.pbkdf2_hmac (viene con Python, no hace
# falta instalar nada). El resultado se guarda como "salt$hash",
# los dos en hexadecimal, en una sola columna de texto.
# =========================================================

def hash_password(password: str) -> str:

    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )

    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:

    if not stored or "$" not in stored:
        return False

    salt, hex_digest = stored.split("$", 1)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )

    return secrets.compare_digest(
        digest.hex(),
        hex_digest
    )


# =========================================================
# GENERAR API KEY
# =========================================================

def generate_api_key():

    return (
        "zb_live_"
        + secrets.token_urlsafe(32)
    )


# =========================================================
# CREAR EMPRESA
# =========================================================

def create_company(
    db: Session,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    website: str | None = None
):

    api_key = generate_api_key()

    company = Company(
        name=name,
        email=email,
        phone=phone,
        website=website,
        api_key=api_key
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


# =========================================================
# OBTENER EMPRESA POR ID
# =========================================================

def get_company(
    db: Session,
    company_id: int
):

    return (
        db.query(Company)
        .filter(
            Company.id == company_id
        )
        .first()
    )


# =========================================================
# OBTENER TODAS LAS EMPRESAS
# =========================================================

def get_companies(
    db: Session
):

    return (
        db.query(Company)
        .order_by(
            Company.id.desc()
        )
        .all()
    )


# =========================================================
# OBTENER EMPRESA POR API KEY
# =========================================================

def get_company_by_api_key(
    db: Session,
    api_key: str
):

    return (
        db.query(Company)
        .filter(
            Company.api_key == api_key
        )
        .first()
    )


# =========================================================
# ACTUALIZAR KNOWLEDGE
# =========================================================

def update_company_knowledge(
    db: Session,
    company_id: int,
    knowledge: str
):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:
        return None

    company.knowledge = knowledge

    db.commit()
    db.refresh(company)

    return company


# =========================================================
# ACTUALIZAR APARIENCIA DEL WIDGET
# =========================================================

def update_company_appearance(
    db: Session,
    company_id: int,
    primary_color: str | None = None,
    icon: str | None = None,
    icon_has_background: bool | None = None
):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:
        return None

    if primary_color:
        company.primary_color = primary_color

    if icon:
        company.icon = icon

    # OJO: acá sí hay que comparar con "is not None", no usar
    # "if icon_has_background" a secas — False es un valor
    # válido (significa "sin fondo") y en Python False es
    # "falsy", así que "if icon_has_background:" nunca dejaría
    # guardar la opción de sacar el fondo.
    if icon_has_background is not None:
        company.icon_has_background = icon_has_background

    db.commit()
    db.refresh(company)

    return company


# =========================================================
# GENERAR API KEY PARA EMPRESA EXISTENTE
# =========================================================

def generate_company_api_key(
    db: Session,
    company_id: int
):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:
        return None

    # Si ya tiene una API Key, conservarla
    if company.api_key:
        return company

    company.api_key = generate_api_key()

    db.commit()
    db.refresh(company)

    return company


# =========================================================
# REGENERAR API KEY
# =========================================================

def regenerate_company_api_key(
    db: Session,
    company_id: int
):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:
        return None

    company.api_key = generate_api_key()

    db.commit()
    db.refresh(company)

    return company


# =========================================================
# OBTENER EMPRESA POR EMAIL
#
# El email es el "usuario" con el que el cliente entra a su
# propia vista (portal).
# =========================================================

def get_company_by_email(
    db: Session,
    email: str
):

    return (
        db.query(Company)
        .filter(
            Company.email == email
        )
        .first()
    )


# =========================================================
# FIJAR CONTRASEÑA DE ACCESO DEL CLIENTE
#
# La define el admin desde su panel, para dársela al cliente
# junto con su email.
# =========================================================

def set_company_portal_password(
    db: Session,
    company_id: int,
    password: str
):

    company = get_company(
        db=db,
        company_id=company_id
    )

    if not company:
        return None

    company.portal_password_hash = hash_password(password)

    db.commit()
    db.refresh(company)

    return company


# =========================================================
# VALIDAR LOGIN DEL CLIENTE
#
# Devuelve la empresa si el email y la contraseña son correctos,
# o None si no (email no existe, no tiene contraseña configurada
# todavía, o la contraseña no coincide).
# =========================================================

def verify_company_login(
    db: Session,
    email: str,
    password: str
):

    company = get_company_by_email(
        db=db,
        email=email
    )

    if not company:
        return None

    if not company.portal_password_hash:
        return None

    if not verify_password(password, company.portal_password_hash):
        return None

    return company