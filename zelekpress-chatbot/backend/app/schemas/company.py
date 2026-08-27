from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    logo: str | None = None


class CompanyOut(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    plan_id: int | None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    logo: str | None = None

    model_config = {"from_attributes": True}


class MemberInvite(BaseModel):
    email: str
    role: str = "agent"


class MemberOut(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    role: str
