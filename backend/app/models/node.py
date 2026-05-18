from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ForeignKey, JSON, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Node(Base):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="节点编码")
    node_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="节点名称")
    agency_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agency.id"), nullable=False, comment="所属机构ID")

    node_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="节点类型: integrated_node/service_node/data_node/compute_node/blockchain_node/gateway_node")
    node_role: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="节点角色")
    node_capabilities: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="节点能力: data/compute/service/chain")

    # 网络地址
    service_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="服务URL")
    internal_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="内网IP")
    public_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="公网IP")
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="节点访问地址(兼容旧字段)")
    health_check_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="健康检查URL")

    # SecretFlow / Ray 计算配置
    ray_address: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Ray集群地址")

    # 区块链节点配置
    chain_type: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="链类型")
    chain_node_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="链节点ID")
    rpc_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="RPC接入点")
    p2p_endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="P2P接入点")
    anchor_service_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="存证服务URL")
    contract_address: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="合约地址")
    cert_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证书ID")

    # 状态
    status: Mapped[str] = mapped_column(String(32), default="registered", nullable=False, comment="节点状态: registered/checking/active/offline/disabled/failed")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后心跳时间(兼容旧字段)")
    last_heartbeat_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后心跳时间")

    # Agent控制
    agent_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="节点Agent控制服务地址")
    agent_token: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="节点Agent访问令牌")
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次检测时间")
    last_check_result: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="最近一次检测结果")
    activation_status: Mapped[str] = mapped_column(String(32), default="not_activated", nullable=False, comment="激活状态: not_activated/activating/activated/activation_failed")
    activation_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="激活说明")

    # 资源配置
    cpu_total: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="CPU总量(核)")
    memory_total: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="内存总量(MB)")
    gpu_total: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="GPU总量")
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="最大并发任务数")
    current_running_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="当前运行任务数")
    node_load_status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False, comment="负载状态: idle/busy/offline/disabled")
    resource_desc_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="资源描述JSON")

    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_node_code", "node_code"),
        Index("idx_node_agency_id", "agency_id"),
        Index("idx_node_type", "node_type"),
        Index("idx_node_status", "status"),
        Index("idx_node_load_status", "node_load_status"),
    )
