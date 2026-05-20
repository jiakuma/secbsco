from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=False, comment="所属机构ID")
    node_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("node.id"), nullable=True, comment="所属节点ID")

    dataset_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="数据集编码")
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="数据集名称")
    data_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="数据类型: file/database/api")
    data_location: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="数据位置")

    dataset_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="数据集类型(扩展)")
    storage_uri: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="数据存储地址(扩展)")
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="字段结构")
    template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="数据模板ID")
    status: Mapped[str] = mapped_column(String(32), default="enabled", nullable=False, comment="状态: enabled/disabled")
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False, comment="版本号")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人ID")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_dataset_agency_id", "agency_id"),
        Index("idx_dataset_node_id", "node_id"),
        Index("idx_dataset_code", "dataset_code"),
        Index("idx_dataset_data_type", "data_type"),
        Index("idx_dataset_status", "status"),
    )