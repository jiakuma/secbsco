from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    task_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="任务编码")
    task_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="任务名称")

    # 关联字段（旧字段保持不变，ForeignKey 保持引用 sys_user/agency）
    creator_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=True, comment="创建用户ID")
    creator_agency_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=True, comment="创建机构ID")
    template_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("stat_template.id"), nullable=True, comment="统计模板ID")

    # 统计参数
    stat_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="统计开始时间")
    stat_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="统计结束时间")
    params_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="任务参数")

    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False, comment="任务状态")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    # ---- 新增字段（均可为空，兼容历史数据）----
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属群组ID")
    lead_agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="牵头机构ID")
    execution_mode: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="执行模式: auto/manual")
    selected_node_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="选定节点JSON")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_task_group_id", "group_id"),
        Index("idx_task_status", "status"),
    )
