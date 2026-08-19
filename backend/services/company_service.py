import secrets

from sqlalchemy.orm import Session

from models import Company


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
    icon: str | None = None
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