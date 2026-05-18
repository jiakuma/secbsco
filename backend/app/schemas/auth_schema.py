"""认证相关 Schema。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


# ---- Login Response ----

class LoginUserInfo(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    agency_id: int | None = None
    agency_name: str | None = None


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: LoginUserInfo


# ---- /me Response ----

class RoleInfo(BaseModel):
    role_code: str
    scope_type: str
    scope_id: int | None = None


class GroupInfoItem(BaseModel):
    group_id: int
    group_code: str
    group_name: str
    status: str


class MeResponseData(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    agency_id: int | None = None
    agency_name: str | None = None
    current_group_id: int | None = None
    roles: list[RoleInfo]
    groups: list[GroupInfoItem]
    permissions: list[str]


# ---- /menus Response ----

class MenuItem(BaseModel):
    title: str
    path: str
    icon: str | None = None
