from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContractInfo(Base):
    """合约信息表"""
    __tablename__ = "contract_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contract_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="合约名称")
    contract_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="合约版本")
    contract_address: Mapped[str] = mapped_column(String(128), nullable=False, comment="合约地址")
    chain_type: Mapped[str] = mapped_column(String(64), default="fisco_bcos", nullable=False, comment="链类型")
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False,
                                        comment="状态: active/disabled/archived")
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="部署时间")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("chain_type", "contract_address", name="uk_contract_chain_address"),
        Index("idx_contract_name", "contract_name"),
        Index("idx_contract_address", "contract_address"),
        Index("idx_contract_status", "status"),
    )
