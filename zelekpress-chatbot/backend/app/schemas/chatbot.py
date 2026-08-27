from pydantic import BaseModel, Field


class ChatbotCreate(BaseModel):
    name_public: str = Field(min_length=1, max_length=150)
    name_internal: str | None = Field(default=None, max_length=150)
    description: str | None = None
    language: str = "es"


class ChatbotUpdate(BaseModel):
    name_public: str | None = None
    name_internal: str | None = None
    description: str | None = None
    avatar: str | None = None
    logo: str | None = None
    language: str | None = None
    status: str | None = None  # active | paused


class ChatbotOut(BaseModel):
    id: int
    company_id: int
    name_internal: str
    name_public: str
    description: str | None = None
    avatar: str | None = None
    logo: str | None = None
    language: str
    status: str
    allowed_domains: list | None = None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    system_prompt: str | None = None
    personality: str | None = None
    greeting_message: str | None = None
    unknown_message: str | None = None
    farewell_message: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8000)
    behavior: dict | None = None


class SettingsOut(BaseModel):
    chatbot_id: int
    system_prompt: str | None = None
    personality: str | None = None
    greeting_message: str | None = None
    unknown_message: str | None = None
    farewell_message: str | None = None
    model: str | None = None
    temperature: float
    max_tokens: int
    behavior: dict | None = None

    model_config = {"from_attributes": True}


class DomainsUpdate(BaseModel):
    allowed_domains: list[str] = Field(default_factory=list)


class WidgetConfigOut(BaseModel):
    """Config pública que consume el widget (sin secretos)."""
    id: int
    name_public: str
    avatar: str | None = None
    logo: str | None = None
    language: str
    greeting_message: str | None = None
    appearance: dict = {}   # tokens de diseño completos (default + overrides)


class SessionOut(BaseModel):
    session_id: str
    greeting: str | None = None


class PublicMessageIn(BaseModel):
    message: str
    session_id: str | None = None


class PublicMessageOut(BaseModel):
    reply: str | None = None   # None cuando está en modo humano (responde un agente)
    session_id: str


class SessionRef(BaseModel):
    session_id: str | None = None
