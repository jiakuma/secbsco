"""认证相关 API：登录、当前用户、菜单。"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.sys_user import SysUser
from app.models.agency import Agency
from app.schemas.auth_schema import LoginRequest
from app.services.auth_service import AuthService
from app.services.access_control_service import (
    get_user_context,
    write_operate_log,
)
from app.services.menu_service import get_menus_for_roles
from app.utils.response import success, fail


router = APIRouter(prefix="/api/auth", tags=["登录认证"])


def _build_user_dict(user: SysUser) -> dict:
    """构建基础用户信息字典。"""
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "agency_id": user.agency_id,
        "agency_name": None,
        "status": user.status,
    }


def _build_login_response_data(user: SysUser, access_token: str) -> dict:
    """构建登录响应数据。"""
    # 尝试获取机构名称
    agency_name = None
    if user.agency_id:
        from app.models.agency import Agency
        from app.core.database import SessionLocal
        # 使用传入的 db session 比创建新 session 更好，但 login 中不方便传递
        # 这里直接在 login handler 中处理

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "agency_id": user.agency_id,
            "agency_name": agency_name,
        },
    }


@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    用户登录。

    逻辑：
    1. 根据 username 查询 sys_user
    2. 校验 status = active
    3. 校验 password_hash
    4. 生成 JWT token（含 user_id、username）
    5. 更新 last_login_time、last_login_ip
    6. 写入 sys_user_operate_log
    """
    user = AuthService.authenticate_user(
        db=db,
        username=req.username,
        password=req.password,
    )

    if not user:
        return fail(message="用户名或密码错误，或用户已被禁用", code=401)

    # 获取机构名称
    agency_name = None
    if user.agency_id:
        from app.models.agency import Agency
        agency = db.query(Agency).filter(Agency.id == user.agency_id).first()
        if agency:
            agency_name = agency.agency_name

    # 生成 token
    access_token = create_access_token(
        subject=str(user.id),
        extra_data={
            "username": user.username,
        },
    )

    # 更新登录信息
    ip_address = None
    if request.client:
        ip_address = request.client.host

    user.last_login_time = datetime.now()
    user.last_login_ip = ip_address
    db.commit()
    db.refresh(user)

    # 写入操作日志
    write_operate_log(
        db=db,
        user_id=user.id,
        username=user.username,
        operation_type="USER_LOGIN",
        request=request,
        agency_id=user.agency_id,
    )
    db.commit()

    return success({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "agency_id": user.agency_id,
            "agency_name": agency_name,
        },
    })


@router.get("/me")
def get_me(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户完整信息。

    返回：用户基础信息 + 机构名称 + 群组 + 角色 + 权限 + 当前群组
    """
    ctx = get_user_context(db, current_user.id)

    return success({
        "id": ctx["user"].id,
        "username": ctx["user"].username,
        "real_name": ctx["user"].real_name,
        "agency_id": ctx["user"].agency_id,
        "agency_name": ctx["agency_name"],
        "current_group_id": ctx["current_group_id"],
        "roles": ctx["roles"],
        "groups": ctx["groups"],
        "permissions": ctx["permissions"],
    })


@router.get("/menus")
def get_menus(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    根据当前用户角色返回菜单列表。
    """
    ctx = get_user_context(db, current_user.id)
    menus = get_menus_for_roles(ctx["roles"])
    return success(menus)


@router.post("/logout")
def logout(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """退出登录。"""
    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="USER_LOGOUT",
        agency_id=current_user.agency_id,
    )
    db.commit()

    return success(message="退出成功")


@router.post("/dev-switch")
def dev_switch_user(
    req: dict,
    db: Session = Depends(get_db),
):
    """开发环境切换用户（无需验证密码）。"""
    user_id = req.get("user_id")
    username = req.get("username")

    if not user_id and not username:
        raise HTTPException(status_code=400, detail="需要提供 user_id 或 username")

    user = None
    if user_id:
        user = db.query(SysUser).filter(SysUser.id == user_id).first()
    elif username:
        user = db.query(SysUser).filter(SysUser.username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.status != "active":
        raise HTTPException(status_code=400, detail="用户已禁用")

    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"username": user.username},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )

    agency_name = None
    if user.agency_id:
        agency = db.query(Agency).filter(Agency.id == user.agency_id).first()
        agency_name = agency.agency_name if agency else None

    return success({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "agency_id": user.agency_id,
            "agency_name": agency_name,
        },
    })
