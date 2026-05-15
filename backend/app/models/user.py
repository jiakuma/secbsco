from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SysRole(Base):
    """角色表"""
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="角色编码: admin/user/governor")
    role_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="角色名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/disabled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_sys_role_code", "role_code"),
        Index("idx_sys_role_status", "status"),
    )


class SysUserGroup(Base):
    """用户群组关系表"""
    __tablename__ = "sys_user_group"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="群组ID")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属机构ID")
    join_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False,
                                              comment="加入状态: active/disabled/archived")
    authorized_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="授权人用户ID")
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="授权时间")
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="禁用时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uk_sys_user_group_user_group"),
        Index("idx_sys_user_group_user_id", "user_id"),
        Index("idx_sys_user_group_group_id", "group_id"),
        Index("idx_sys_user_group_agency_id", "agency_id"),
        Index("idx_sys_user_group_status", "join_status"),
    )


class SysUserRoleBinding(Base):
    """用户角色作用域绑定表"""
    __tablename__ = "sys_user_role_binding"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    role_code: Mapped[str] = mapped_column(String(32), nullable=False, comment="角色编码: admin/user/governor")
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="作用域类型: platform/agency/group")
    scope_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="作用域ID (platform时为null)")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False,
                                        comment="状态: active/disabled/archived")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="禁用时间")

    __table_args__ = (
        UniqueConstraint("user_id", "role_code", "scope_type", "scope_id", name="uk_user_role_scope"),
        Index("idx_user_role_binding_user_id", "user_id"),
        Index("idx_user_role_binding_role_code", "role_code"),
        Index("idx_user_role_binding_scope", "scope_type", "scope_id"),
        Index("idx_user_role_binding_status", "status"),
    )


class SysUserOperateLog(Base):
    """用户操作日志表"""
    __tablename__ = "sys_user_operate_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="用户ID")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="用户名")
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作类型")
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="资源类型")
    resource_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="资源ID")
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="群组ID")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="机构ID")
    request_path: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="请求路径")
    request_method: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="请求方法")
    request_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="请求参数JSON")
    result_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="结果状态")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="IP地址")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_operate_log_user_id", "user_id"),
        Index("idx_operate_log_group_id", "group_id"),
        Index("idx_operate_log_agency_id", "agency_id"),
        Index("idx_operate_log_operation_type", "operation_type"),
        Index("idx_operate_log_created_at", "created_at"),
    )
