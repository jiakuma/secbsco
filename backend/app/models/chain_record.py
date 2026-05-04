from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChainRecord(Base):
    __tablename__ = "chain_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    biz_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务ID")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, comment="内容哈希")

    chain_type: Mapped[str] = mapped_column(String(64), default="fisco_bcos", nullable=False, comment="链类型")
    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="交易哈希")
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="区块高度")
    contract_address: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="合约地址")

    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False, comment="存证状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)