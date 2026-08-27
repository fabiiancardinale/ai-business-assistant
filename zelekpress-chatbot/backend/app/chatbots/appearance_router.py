"""Fase 3 — Personalización: apariencia del chatbot, presets y biblioteca de
temas por empresa. La apariencia son 'tokens' que consumen tanto el preview
en tiempo real como el widget real."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_tenant, require_role, TenantContext
from app.core.themes import PRESET_THEMES, DEFAULT_APPEARANCE, full_appearance, _merge
from app.core.uploads import save_image
from app.models.chatbot import Chatbot, ChatbotTheme
from app.models.audit import AuditLog
from app.schemas.theme import (
    AppearanceUpdate, AppearanceOut, PresetOut, ThemeCreate, ThemeOut,
)

router = APIRouter(prefix="/api/v1", tags=["appearance"])


def _bot(db: Session, tenant: TenantContext, chatbot_id: int) -> Chatbot:
    bot = db.get(Chatbot, chatbot_id)
    if not bot or bot.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Chatbot no encontrado")
    return bot


# ---------------------- Presets (temas predefinidos) ----------------------

@router.get("/themes/presets", response_model=list[PresetOut])
def list_presets(_: TenantContext = Depends(get_tenant)):
    return [PresetOut(key=k, label=v["label"], tokens=v["tokens"]) for k, v in PRESET_THEMES.items()]


# ---------------------- Apariencia del chatbot ----------------------

@router.get("/chatbots/{chatbot_id}/appearance", response_model=AppearanceOut)
def get_appearance(chatbot_id: int, tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    bot = _bot(db, tenant, chatbot_id)
    return AppearanceOut(
        chatbot_id=bot.id,
        appearance=full_appearance(bot.appearance),
        raw=bot.appearance or {},
    )


@router.put("/chatbots/{chatbot_id}/appearance", response_model=AppearanceOut)
def update_appearance(
    chatbot_id: int, data: AppearanceUpdate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _bot(db, tenant, chatbot_id)
    # Mergeamos lo nuevo sobre lo ya guardado (no se pierde lo anterior).
    bot.appearance = _merge(bot.appearance or {}, data.appearance)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id,
                    action="update", entity="chatbot_appearance", entity_id=bot.id))
    db.commit()
    db.refresh(bot)
    return AppearanceOut(chatbot_id=bot.id, appearance=full_appearance(bot.appearance), raw=bot.appearance or {})


@router.post("/chatbots/{chatbot_id}/appearance/apply-preset/{preset_key}", response_model=AppearanceOut)
def apply_preset(
    chatbot_id: int, preset_key: str,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if preset_key not in PRESET_THEMES:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    bot = _bot(db, tenant, chatbot_id)
    bot.appearance = _merge(bot.appearance or {}, PRESET_THEMES[preset_key]["tokens"])
    db.commit()
    db.refresh(bot)
    return AppearanceOut(chatbot_id=bot.id, appearance=full_appearance(bot.appearance), raw=bot.appearance or {})


# ---------------------- Subida de imágenes (launcher / logo) ----------------------

@router.post("/chatbots/{chatbot_id}/appearance/image", response_model=AppearanceOut)
def upload_appearance_image(
    chatbot_id: int,
    target: str = "launcher",   # launcher | logo | avatar
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Sube una imagen (PNG/JPG/WEBP) y la usa como ícono del launcher, logo
    del header o avatar del bot, según `target`."""
    if target not in ("launcher", "logo", "avatar"):
        raise HTTPException(status_code=400, detail="target inválido")

    bot = _bot(db, tenant, chatbot_id)
    url = save_image(
        file,
        subdir=f"appearance/company_{tenant.company.id}",
        name=f"chatbot_{bot.id}_{target}",
    )

    # Guardamos la URL en el token correspondiente.
    if target == "launcher":
        override = {"launcher": {"image": url}}
    elif target == "logo":
        override = {"header": {"logo": url}, "logo_url": url}
        bot.logo = url
    else:  # avatar
        override = {"messages": {"bot_avatar": url}}
        bot.avatar = url

    bot.appearance = _merge(bot.appearance or {}, override)
    db.add(AuditLog(company_id=tenant.company.id, user_id=tenant.user.id,
                    action="upload", entity="chatbot_appearance", entity_id=bot.id))
    db.commit()
    db.refresh(bot)
    return AppearanceOut(chatbot_id=bot.id, appearance=full_appearance(bot.appearance), raw=bot.appearance or {})


# ---------------------- Biblioteca de temas por empresa ----------------------

@router.get("/themes", response_model=list[ThemeOut])
def list_company_themes(tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)):
    rows = db.execute(
        select(ChatbotTheme).where(ChatbotTheme.company_id == tenant.company.id).order_by(ChatbotTheme.id.desc())
    ).scalars().all()
    return [ThemeOut.model_validate(t) for t in rows]


@router.post("/themes", response_model=ThemeOut, status_code=201)
def create_theme(
    data: ThemeCreate,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    theme = ChatbotTheme(
        company_id=tenant.company.id, name=data.name,
        base_theme=data.base_theme, tokens=data.tokens,
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return ThemeOut.model_validate(theme)


@router.delete("/themes/{theme_id}", status_code=204)
def delete_theme(
    theme_id: int,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    theme = db.get(ChatbotTheme, theme_id)
    if not theme or theme.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    db.delete(theme)
    db.commit()
    return None


@router.post("/chatbots/{chatbot_id}/appearance/apply-theme/{theme_id}", response_model=AppearanceOut)
def apply_company_theme(
    chatbot_id: int, theme_id: int,
    tenant: TenantContext = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    bot = _bot(db, tenant, chatbot_id)
    theme = db.get(ChatbotTheme, theme_id)
    if not theme or theme.company_id != tenant.company.id:
        raise HTTPException(status_code=404, detail="Tema no encontrado")
    bot.appearance = _merge(bot.appearance or {}, theme.tokens or {})
    db.commit()
    db.refresh(bot)
    return AppearanceOut(chatbot_id=bot.id, appearance=full_appearance(bot.appearance), raw=bot.appearance or {})
