from dataclasses import asdict
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.sys_user import SysUser
from app.models.agency import Agency
from app.utils.response import success, fail
from ..adapters.persistence import (
    SQLAlchemyUserRepository, BridgeAuthPort, BridgeAccessControlPort,
    BridgeAuditLogPort, BridgeMenuPort, BridgeAgencyQueryPort,
)
from ..adapters.schemas import LoginRequest
from ..application.use_cases import LoginUseCase, GetCurrentUserUseCase, GetMenusUseCase, LogoutUseCase


router = APIRouter(prefix="/api/auth", tags=["登录认证"])


@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_repo = SQLAlchemyUserRepository(db)
    auth = BridgeAuthPort(db)
    audit = BridgeAuditLogPort()
    agency = BridgeAgencyQueryPort(db)
    uc = LoginUseCase(auth, audit, agency, user_repo)
    try:
        result = uc.execute(req.username, req.password, db=db, request=request)
        db.commit()
        return success(asdict(result))
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code == 401:
            return fail(message=e.detail, code=401)
        raise


@router.get("/me")
def get_me(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    access_control = BridgeAccessControlPort(db)
    uc = GetCurrentUserUseCase(access_control)
    result = uc.execute(current_user.id)
    return success(asdict(result))


@router.get("/menus")
def get_menus(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    access_control = BridgeAccessControlPort(db)
    menu = BridgeMenuPort()
    uc = GetMenusUseCase(access_control, menu)
    result = uc.execute(current_user.id)
    return success(result)


@router.post("/logout")
def logout(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audit = BridgeAuditLogPort()
    uc = LogoutUseCase(audit)
    uc.execute(current_user, db=db)
    db.commit()
    return success(message="退出成功")


@router.post("/dev-switch")
def dev_switch_user(
    req: dict,
    db: Session = Depends(get_db),
):
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
        subject=str(user.id), extra_data={"username": user.username},
        expires_delta=timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )
    agency_name = None
    if user.agency_id:
        agency = db.query(Agency).filter(Agency.id == user.agency_id).first()
        agency_name = agency.agency_name if agency else None
    return success({
        "access_token": access_token, "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        "user": {"id": user.id, "username": user.username, "real_name": user.real_name,
                 "agency_id": user.agency_id, "agency_name": agency_name},
    })
