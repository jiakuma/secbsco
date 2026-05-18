from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sys_user import SysUser
from app.core.security import verify_password


class AuthService:

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> SysUser | None:
        return db.query(SysUser).filter(SysUser.username == username).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> SysUser | None:
        return db.query(SysUser).filter(SysUser.id == user_id).first()

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> SysUser | None:
        user = AuthService.get_user_by_username(db, username)

        if not user:
            return None

        if user.status not in ("active",):
            return None

        if not verify_password(password, user.password_hash):
            return None

        user.last_login_at = datetime.now()
        db.commit()
        db.refresh(user)

        return user