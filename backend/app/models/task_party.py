from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskParty(Base):
    __tablename__ = "task_party"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task.id"), nullable=False, comment="任务ID")
    agency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=False, comment="参与机构ID")
    node_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("node.id"), nullable=True, comment="执行节点ID")
    dataset_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("dataset.id"), nullable=True, comment="数据集ID")

    party_role: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="参与方角色")
    field_mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="字段映射")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, comment="参与方状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)