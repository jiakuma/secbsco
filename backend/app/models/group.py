from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, Boolean, Index, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GroupInfo(Base):
    """群组表"""
    __tablename__ = "group_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="群组编码")
    group_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="群组名称")
    group_level: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="群组层级: county/city/province/national")
    region_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="行政区划代码")
    region_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="行政区划名称")
    lead_agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="牵头机构ID")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False,
                                        comment="状态: draft/pending_approval/active/rejected/dissolving/dissolved/archived/disabled")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建用户ID")
    creator_agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人所属机构ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 审批相关字段
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False,
                                                     comment="是否需要审批")
    approval_status: Mapped[str] = mapped_column(String(32), default="none", nullable=False,
                                                  comment="审批状态: none/pending/approved/rejected")
    approval_agency_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True,
                                                             comment="审批机构ID(共同上级)")
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="审批通过人ID")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审批通过时间")
    rejected_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="驳回人ID")
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="驳回时间")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="驳回原因")

    # 生命周期时间戳
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="激活时间")
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="暂停时间")
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="恢复时间")
    dissolving_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发起解散时间")
    dissolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="解散完成时间")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="归档时间")
    dissolve_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="解散原因")
    archive_policy: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="归档策略")

    __table_args__ = (
        Index("idx_group_code", "group_code"),
        Index("idx_group_status", "status"),
        Index("idx_group_lead_agency_id", "lead_agency_id"),
        Index("idx_group_region_code", "region_code"),
    )


class GroupMember(Base):
    """群组成员机构表"""
    __tablename__ = "group_member"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="群组ID")
    agency_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="机构ID")
    member_role: Mapped[str] = mapped_column(String(32), default="participant", nullable=False,
                                             comment="成员角色: lead_agency/participant/data_provider/compute_provider/observer")
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否为牵头机构")
    join_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False,
                                             comment="加入状态: pending/active/removed/disabled/archived")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="加入时间")
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="移出时间")
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="禁用时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "agency_id", name="uk_group_member_group_agency"),
        Index("idx_group_member_group_id", "group_id"),
        Index("idx_group_member_agency_id", "agency_id"),
        Index("idx_group_member_status", "join_status"),
    )


class GroupNode(Base):
    """群组节点授权表"""
    __tablename__ = "group_node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="群组ID")
    agency_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="机构ID")
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="节点ID")
    node_usage_role: Mapped[str] = mapped_column(String(32), nullable=False,
                                                  comment="节点使用角色: group_service/group_data/group_compute/group_blockchain")
    auth_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False,
                                              comment="授权状态: active/disabled/revoked/archived")
    resource_quota_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="资源配额JSON")
    priority_level: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False, comment="优先级")
    max_concurrent_tasks: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False, comment="最大并发任务数")
    usage_policy: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="使用策略")
    authorized_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="授权人用户ID")
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="授权时间")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤销时间")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="归档时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "node_id", name="uk_group_node_group_node"),
        Index("idx_group_node_group_id", "group_id"),
        Index("idx_group_node_node_id", "node_id"),
        Index("idx_group_node_agency_id", "agency_id"),
        Index("idx_group_node_auth_status", "auth_status"),
        Index("idx_group_node_usage_role", "node_usage_role"),
    )


class GroupLifecycleLog(Base):
    """群组生命周期日志表"""
    __tablename__ = "group_lifecycle_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="群组ID")
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="事件类型")
    before_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="变更前状态")
    after_status: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="变更后状态")
    operator_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="操作用户ID")
    operator_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="操作人姓名")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原因")
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="详情JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    __table_args__ = (
        Index("idx_group_lifecycle_group_id", "group_id"),
        Index("idx_group_lifecycle_event_type", "event_type"),
        Index("idx_group_lifecycle_created_at", "created_at"),
    )
