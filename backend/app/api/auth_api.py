from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.models.sys_user import SysUser
from app.schemas.auth_schema import LoginRequest
from app.services.auth_service import AuthService
from app.utils.response import success, fail


router = APIRouter(prefix="/api/auth", tags=["登录认证"])


def build_user_info(user: SysUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "agency_id": user.agency_id,
        "role_code": user.role_code,
        "status": user.status,
    }


@router.post("/login")
def login(
    req: LoginRequest,
    db: Session = Depends(get_db),
):
    user = AuthService.authenticate_user(
        db=db,
        username=req.username,
        password=req.password,
    )

    if not user:
        return fail(
            message="用户名或密码错误，或用户已被禁用",
            code=401,
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_data={
            "username": user.username,
            "role_code": user.role_code,
            "agency_id": user.agency_id,
        },
    )

    return success({
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": build_user_info(user),
    })


@router.get("/me")
def get_me(
    current_user: SysUser = Depends(get_current_user),
):
    return success(build_user_info(current_user))


@router.post("/logout")
def logout():
    return success(message="退出成功")