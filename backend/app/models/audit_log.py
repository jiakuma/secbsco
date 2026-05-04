from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("task.id"), nullable=True, comment="关联任务ID")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=True, comment="机构ID")
    operator_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=True, comment="操作用户ID")

    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作类型")
    object_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="对象类型")
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="对象ID")
    operation_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作描述")
    request_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="请求参数")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="操作结果")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="IP地址")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)