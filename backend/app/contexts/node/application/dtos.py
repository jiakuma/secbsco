from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeDTO:
    id: int | None = None
    node_code: str = ""
    node_name: str = ""
    agency_id: int | None = None
    agency_name: str | None = None
    node_type: str = ""
    node_capabilities: list[str] = field(default_factory=list)
    node_role: str | None = None
    service_url: str | None = None
    endpoint: str | None = None
    internal_ip: str | None = None
    public_ip: str | None = None
    health_check_url: str | None = None
    ray_address: str | None = None
    anchor_service_url: str | None = None
    contract_address: str | None = None
    status: str = ""
    last_heartbeat_at: str | None = None
    node_load_status: str = ""
    agent_url: str | None = None
    agent_token: str | None = None
    last_check_at: str | None = None
    last_check_result: dict | None = None
    activation_status: str = ""
    activation_message: str | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class PaginatedNodesDTO:
    total: int = 0
    page: int = 1
    page_size: int = 10
    items: list[NodeDTO] = field(default_factory=list)


@dataclass
class AgentResultDTO:
    success: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class DeleteResultDTO:
    deleted: bool = True
    node_id: int = 0
