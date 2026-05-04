from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    agency_id: int | None = None
    role_code: str
    status: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_info: UserInfo