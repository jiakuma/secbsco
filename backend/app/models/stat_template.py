from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StatTemplate(Base):
    __tablename__ = "stat_template"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属机构ID")

    template_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="模板编码")
    template_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模板名称")
    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="适用场景")
    exec_mode: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="执行方式: auto/manual")
    output_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="输出结果类型")

    stat_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="统计类型(扩展)")
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="统计指标配置")
    params_schema_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="参数结构配置")
    executor_config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="执行器配置")
    input_requirements_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输入要求")
    output_view_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="输出视图类型")
    template_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="模板哈希")
    status: Mapped[str] = mapped_column(String(32), default="enabled", nullable=False, comment="状态: enabled/disabled")
    version: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False, comment="版本号")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人ID")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模板简介")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_stat_template_agency_id", "agency_id"),
        Index("idx_stat_template_code", "template_code"),
        Index("idx_stat_template_scenario", "scenario"),
        Index("idx_stat_template_status", "status"),
    )