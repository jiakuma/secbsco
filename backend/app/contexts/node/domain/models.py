from dataclasses import dataclass, field
from datetime import datetime
from .enums import NodeStatus, NodeType, ActivationStatus, LoadStatus, NodeCapability, NODE_TYPE_ALIASES, DEFAULT_CAPABILITIES_BY_TYPE


@dataclass
class NodeInfo:
    id: int | None = None
    node_code: str = ""
    node_name: str = ""
    agency_id: int | None = None
    node_type: str = "integrated_node"
    node_role: str | None = None
    node_capabilities: list[str] = field(default_factory=list)
    service_url: str | None = None
    internal_ip: str | None = None
    public_ip: str | None = None
    endpoint: str | None = None
    health_check_url: str | None = None
    ray_address: str | None = None
    chain_type: str | None = None
    chain_node_id: str | None = None
    rpc_endpoint: str | None = None
    p2p_endpoint: str | None = None
    anchor_service_url: str | None = None
    contract_address: str | None = None
    cert_id: str | None = None
    status: str = "registered"
    last_heartbeat_at: datetime | None = None
    last_heartbeat_time: datetime | None = None
    agent_url: str | None = None
    agent_token: str | None = None
    last_check_at: datetime | None = None
    last_check_result: dict | None = None
    activation_status: str = "not_activated"
    activation_message: str | None = None
    cpu_total: int | None = None
    memory_total: int | None = None
    gpu_total: int | None = None
    max_concurrent_tasks: int = 1
    current_running_tasks: int = 0
    node_load_status: str = "idle"
    resource_desc_json: dict | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def enable(self) -> None:
        self.status = NodeStatus.ACTIVE.value
        self.node_load_status = LoadStatus.IDLE.value
        self.updated_at = datetime.now()

    def disable(self) -> None:
        self.status = NodeStatus.DISABLED.value
        self.node_load_status = LoadStatus.DISABLED.value
        self.updated_at = datetime.now()

    def set_status(self, status: str) -> None:
        valid = {s.value for s in NodeStatus}
        if status not in valid:
            raise ValueError(f"节点状态不合法: {status}")
        self.status = status
        if status == NodeStatus.DISABLED.value:
            self.node_load_status = LoadStatus.DISABLED.value
        elif status == NodeStatus.OFFLINE.value:
            self.node_load_status = LoadStatus.OFFLINE.value
        else:
            self.node_load_status = LoadStatus.IDLE.value
        self.updated_at = datetime.now()

    def record_check(self, result: dict, agent_reachable: bool, http_ok: bool = True) -> None:
        self.last_check_at = datetime.now()
        self.last_check_result = result
        self.activation_message = result.get("message", "节点检测完成")
        if agent_reachable and http_ok:
            if self.status in {NodeStatus.OFFLINE.value, NodeStatus.FAILED.value, NodeStatus.CHECKING.value}:
                self.status = NodeStatus.REGISTERED.value
        elif not agent_reachable:
            self.status = NodeStatus.OFFLINE.value
            self.activation_message = f"Agent 不可达：{result.get('error', '')}"
        elif not http_ok:
            self.status = NodeStatus.FAILED.value
            self.activation_message = result.get("message", "节点检测失败")
        self.updated_at = datetime.now()

    def start_activation(self) -> None:
        self.status = NodeStatus.CHECKING.value
        self.activation_status = ActivationStatus.ACTIVATING.value
        self.activation_message = "正在调用节点 Agent 执行激活流程..."
        self.updated_at = datetime.now()

    def complete_activation(self, result: dict, success: bool) -> None:
        self.last_check_at = datetime.now()
        self.last_check_result = result
        if success:
            self.status = NodeStatus.ACTIVE.value
            self.activation_status = ActivationStatus.ACTIVATED.value
            self.activation_message = result.get("message", "节点激活成功")
            self.node_load_status = LoadStatus.IDLE.value
        else:
            self.status = NodeStatus.FAILED.value
            self.activation_status = ActivationStatus.ACTIVATION_FAILED.value
            self.activation_message = result.get("message") or result.get("error") or "节点激活失败"
            self.node_load_status = LoadStatus.OFFLINE.value
        self.updated_at = datetime.now()

    def complete_deactivation(self, result: dict, success: bool) -> None:
        self.last_check_at = datetime.now()
        self.last_check_result = result
        if success:
            self.status = NodeStatus.DISABLED.value
            self.activation_status = ActivationStatus.NOT_ACTIVATED.value
            self.activation_message = result.get("message", "节点已停用")
            self.node_load_status = LoadStatus.DISABLED.value
        else:
            self.activation_message = result.get("message") or result.get("error") or "节点停用失败"
        self.updated_at = datetime.now()

    def fail_activation(self, error: str) -> None:
        self.status = NodeStatus.FAILED.value
        self.activation_status = ActivationStatus.ACTIVATION_FAILED.value
        self.activation_message = f"节点激活失败：{error}"
        self.last_check_at = datetime.now()
        self.last_check_result = {"success": False, "error": error, "message": f"节点激活失败：{error}"}
        self.node_load_status = LoadStatus.OFFLINE.value
        self.updated_at = datetime.now()

    def fail_deactivation(self, error: str) -> None:
        self.activation_message = f"节点停用失败：{error}"
        self.last_check_at = datetime.now()
        self.last_check_result = {"success": False, "error": error, "message": f"节点停用失败：{error}"}
        self.updated_at = datetime.now()

    @staticmethod
    def normalize_node_type(node_type: str | None) -> str:
        value = (node_type or "integrated_node").strip()
        value = NODE_TYPE_ALIASES.get(value, value)
        valid = {t.value for t in NodeType}
        if value not in valid:
            raise ValueError(f"节点类型不合法: {value}")
        return value

    @staticmethod
    def normalize_capabilities(node_type: str, capabilities) -> list[str]:
        if capabilities is None or capabilities == "":
            raw_values = [c.value for c in DEFAULT_CAPABILITIES_BY_TYPE.get(NodeType(node_type), [])]
        elif isinstance(capabilities, str):
            raw_values = [item.strip() for item in capabilities.split(",") if item.strip()]
        elif isinstance(capabilities, (list, tuple, set)):
            raw_values = list(capabilities)
        else:
            raise ValueError("节点能力格式不合法")
        valid_caps = {c.value for c in NodeCapability}
        normalized: list[str] = []
        for item in raw_values:
            value = str(item).strip()
            if not value:
                continue
            if value not in valid_caps:
                raise ValueError(f"节点能力不合法：{value}")
            if value not in normalized:
                normalized.append(value)
        if not normalized:
            default = DEFAULT_CAPABILITIES_BY_TYPE.get(NodeType(node_type), [])
            normalized = [c.value for c in default]
        if not normalized:
            raise ValueError("节点能力不能为空")
        return normalized
