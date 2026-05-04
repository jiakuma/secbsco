from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Node(Base):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=False, comment="所属机构ID")

    node_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="节点编码")
    node_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点名称")
    node_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="节点类型")
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="节点访问地址")
    status: Mapped[str] = mapped_column(String(32), default="offline", nullable=False, comment="节点状态")

    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后心跳时间")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)