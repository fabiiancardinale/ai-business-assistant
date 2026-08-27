from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = None
    price: float = 0
    currency: str = "CLP"
    period: str = "monthly"
    limits: dict | None = None
    features: dict | None = None
    active: bool = True
    position: int = 0


class PlanUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    currency: str | None = None
    period: str | None = None
    limits: dict | None = None
    features: dict | None = None
    active: bool | None = None
    position: int | None = None


class PlanOut(BaseModel):
    id: int
    name: str
    slug: str
    price: float
    currency: str
    period: str
    limits: dict | None
    features: dict | None
    active: bool
    position: int

    model_config = {"from_attributes": True}
