from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserCreate(BaseModel):
    username: str = Field(..., max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    real_name: str | None = Field(default=None, max_length=64, description="真实姓名")
    phone: str | None = Field(default=None, max_length=64, description="手机号")
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    agency_id: int | None = Field(default=None, description="所属机构ID")
    status: str = Field(default="active", max_length=32, description="状态")


class UserUpdate(BaseModel):
    real_name: str | None = Field(default=None, max_length=64, description="真实姓名")
    phone: str | None = Field(default=None, max_length=64, description="手机号")
    email: str | None = Field(default=None, max_length=128, description="邮箱")
    agency_id: int | None = Field(default=None, description="所属机构ID")
    status: str | None = Field(default=None, max_length=32, description="状态")


class RoleBindRequest(BaseModel):
    role_code: str = Field(..., description="角色编码: admin/user/governor")
    scope_type: str = Field(..., description="作用域: platform/agency/group")
    scope_id: int | None = Field(default=None, description="作用域ID")


class GroupBindRequest(BaseModel):
    group_id: int = Field(..., description="群组ID")
    agency_id: int | None = Field(default=None, description="所属机构ID")
