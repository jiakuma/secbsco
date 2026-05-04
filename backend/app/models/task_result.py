from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskResult(Base):
    __tablename__ = "task_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task.id"), unique=True, nullable=False, comment="任务ID")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="结果JSON")
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="指标明细")
    result_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="结果哈希")
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False, comment="结果状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)