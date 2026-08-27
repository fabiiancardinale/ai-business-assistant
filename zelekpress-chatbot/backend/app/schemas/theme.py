from pydantic import BaseModel, Field


class AppearanceUpdate(BaseModel):
    """Tokens de apariencia (parciales; se mergean sobre lo existente)."""
    appearance: dict = Field(default_factory=dict)


class AppearanceOut(BaseModel):
    chatbot_id: int
    appearance: dict          # apariencia COMPLETA (default + overrides)
    raw: dict | None = None   # solo los overrides guardados


class PresetOut(BaseModel):
    key: str
    label: str
    tokens: dict


class ThemeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_theme: str | None = None
    tokens: dict = Field(default_factory=dict)


class ThemeOut(BaseModel):
    id: int
    name: str
    base_theme: str | None = None
    tokens: dict | None = None

    model_config = {"from_attributes": True}
