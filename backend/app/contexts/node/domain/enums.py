from enum import Enum


class NodeType(str, Enum):
    INTEGRATED = "integrated_node"
    SERVICE = "service_node"
    DATA = "data_node"
    COMPUTE = "compute_node"
    BLOCKCHAIN = "blockchain_node"
    GATEWAY = "gateway_node"


class NodeStatus(str, Enum):
    REGISTERED = "registered"
    CHECKING = "checking"
    ACTIVE = "active"
    OFFLINE = "offline"
    DISABLED = "disabled"
    FAILED = "failed"


class NodeCapability(str, Enum):
    DATA = "data"
    COMPUTE = "compute"
    SERVICE = "service"
    CHAIN = "chain"


class ActivationStatus(str, Enum):
    NOT_ACTIVATED = "not_activated"
    ACTIVATING = "activating"
    ACTIVATED = "activated"
    ACTIVATION_FAILED = "activation_failed"


class LoadStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    DISABLED = "disabled"


NODE_TYPE_ALIASES = {"chain_node": "blockchain_node"}

DEFAULT_CAPABILITIES_BY_TYPE = {
    NodeType.INTEGRATED: [NodeCapability.DATA, NodeCapability.COMPUTE, NodeCapability.SERVICE, NodeCapability.CHAIN],
    NodeType.DATA: [NodeCapability.DATA],
    NodeType.COMPUTE: [NodeCapability.COMPUTE],
    NodeType.SERVICE: [NodeCapability.SERVICE],
    NodeType.BLOCKCHAIN: [NodeCapability.CHAIN],
    NodeType.GATEWAY: [NodeCapability.SERVICE],
}
