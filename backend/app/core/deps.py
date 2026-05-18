from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.sys_user import SysUser
from app.services.auth_service import AuthService


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> SysUser:
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="未提供 Token"
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Token 类型错误"
        )

    token = credentials.credentials

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="无效或已过期的 Token"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token 缺少用户信息"
        )

    user = AuthService.get_user_by_id(db, int(user_id))

    if not user:
        raise HTTPException(
            status_code=401,
            detail="用户不存在"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=403,
            detail="用户已被禁用"
        )

    return user