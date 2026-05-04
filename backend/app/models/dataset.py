from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=False, comment="所属机构ID")

    dataset_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="数据集编码")
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="数据集名称")
    dataset_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="数据集类型")
    storage_uri: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="数据存储地址")
    schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="字段结构")
    status: Mapped[str] = mapped_column(String(32), default="enabled", nullable=False, comment="状态")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)