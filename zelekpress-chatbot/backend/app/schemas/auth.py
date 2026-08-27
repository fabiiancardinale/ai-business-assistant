from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=2, max_length=150)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_platform_admin: bool

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    company_id: int
    company_name: str
    role: str


class MeOut(BaseModel):
    user: UserOut
    companies: list[MembershipOut]
