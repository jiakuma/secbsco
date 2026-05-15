from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskResult(Base):
    __tablename__ = "task_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 旧字段保持不变
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task.id"), unique=True, nullable=False, comment="任务ID")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="结果JSON")
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="指标明细")
    result_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="结果哈希")
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False, comment="结果状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # ---- 新增字段（均可为空，兼容历史数据）----
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属群组ID")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属机构ID")
    task_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="任务类型: stat/fl_train")
    result_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="结果版本号")
    anchor_status: Mapped[str | None] = mapped_column(String(32), nullable=True,
                                                       comment="上链状态: none/pending/success/failed")
    anchor_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="上链时间")
    chain_record_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="存证记录ID")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_task_result_group_id", "group_id"),
        Index("idx_task_result_anchor_status", "anchor_status"),
    )
