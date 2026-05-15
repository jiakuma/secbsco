from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChainRecord(Base):
    __tablename__ = "chain_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 旧字段保持不变
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

    # ---- 新增字段（均可为空，兼容历史数据）----
    anchor_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="存证业务ID")
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属群组ID")
    agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属机构ID")
    task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联任务ID")
    result_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联结果ID")
    dataset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联数据集ID")
    contract_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="合约名称")
    contract_version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="合约版本")
    verify_status: Mapped[str | None] = mapped_column(String(32), nullable=True,
                                                       comment="验证状态: unverified/verify_success/local_data_changed/chain_mismatch/chain_not_found/query_failed")
    last_verify_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后验证时间")
    verify_detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="验证详情JSON")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="更新时间")

    __table_args__ = (
        Index("idx_chain_record_group_id", "group_id"),
        Index("idx_chain_record_task_id", "task_id"),
        Index("idx_chain_record_verify_status", "verify_status"),
    )
