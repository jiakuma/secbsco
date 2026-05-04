from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StatTemplate(Base):
    __tablename__ = "stat_template"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    template_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="模板编码")
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    stat_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="统计类型")
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="统计指标配置")
    params_schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="参数结构配置")
    status: Mapped[str] = mapped_column(String(32), default="enabled", nullable=False, comment="状态")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)