from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Agency(Base):
    __tablename__ = "agency"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="机构编码")
    agency_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="机构名称")
    agency_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="机构类型: cdc/hospital/lab/health_commission/research/other")
    agency_level: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="机构层级: county/city/province/national")
    parent_agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="上级机构ID")
    region_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="行政区划代码")
    region_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="行政区划名称")
    contact_person: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="联系人")
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="联系电话")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, comment="状态: active/disabled/archived")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_agency_code", "agency_code"),
        Index("idx_agency_status", "status"),
        Index("idx_agency_region_code", "region_code"),
    )
