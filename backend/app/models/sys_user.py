from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="真实姓名")
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="邮箱")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=True, comment="所属机构ID")

    # 兼容旧字段
    role_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="角色编码(旧字段兼容保留)")

    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/disabled/locked/archived")
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最后登录IP")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后登录时间(旧字段兼容保留)")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_sys_user_username", "username"),
        Index("idx_sys_user_agency_id", "agency_id"),
        Index("idx_sys_user_status", "status"),
    )
