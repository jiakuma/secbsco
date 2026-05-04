from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=True, comment="所属机构ID")

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="真实姓名")
    role_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色编码")
    status: Mapped[str] = mapped_column(String(32), default="enabled", nullable=False, comment="状态")

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)