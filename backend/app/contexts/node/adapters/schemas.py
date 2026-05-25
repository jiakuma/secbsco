from pydantic import BaseModel, Field


class NodeCreate(BaseModel):
    node_code: str = Field(..., max_length=64, description="节点编码")
    node_name: str = Field(..., max_length=128, description="节点名称")
    agency_id: int = Field(..., description="所属机构ID")
    node_type: str = Field(default="integrated_node", max_length=32, description="节点类型")
    node_capabilities: list[str] | None = Field(default=None, description="节点能力：data/compute/service/chain")
    node_role: str | None = Field(default=None, max_length=64, description="节点角色")
    service_url: str | None = Field(default=None, max_length=255, description="服务URL")
    endpoint: str | None = Field(default=None, max_length=255, description="节点访问地址")
    internal_ip: str | None = Field(default=None, max_length=64, description="内网IP")
    public_ip: str | None = Field(default=None, max_length=64, description="公网IP")
    health_check_url: str | None = Field(default=None, max_length=255, description="健康检查URL")
    ray_address: str | None = Field(default=None, max_length=128, description="Ray地址")
    anchor_service_url: str | None = Field(default=None, max_length=255, description="存证服务URL")
    contract_address: str | None = Field(default=None, max_length=128, description="合约地址")
    agent_url: str | None = Field(default=None, max_length=255, description="Agent控制服务地址")
    agent_token: str | None = Field(default=None, max_length=255, description="Agent访问令牌")
    description: str | None = Field(default=None, description="描述")


class NodeUpdate(BaseModel):
    node_name: str | None = Field(default=None, max_length=128, description="节点名称")
    agency_id: int | None = Field(default=None, description="所属机构ID")
    node_type: str | None = Field(default=None, max_length=32, description="节点类型")
    node_capabilities: list[str] | None = Field(default=None, description="节点能力：data/compute/service/chain")
    node_role: str | None = Field(default=None, max_length=64, description="节点角色")
    service_url: str | None = Field(default=None, max_length=255, description="服务URL")
    endpoint: str | None = Field(default=None, max_length=255, description="节点访问地址")
    internal_ip: str | None = Field(default=None, max_length=64, description="内网IP")
    public_ip: str | None = Field(default=None, max_length=64, description="公网IP")
    health_check_url: str | None = Field(default=None, max_length=255, description="健康检查URL")
    ray_address: str | None = Field(default=None, max_length=128, description="Ray地址")
    anchor_service_url: str | None = Field(default=None, max_length=255, description="存证服务URL")
    contract_address: str | None = Field(default=None, max_length=128, description="合约地址")
    agent_url: str | None = Field(default=None, max_length=255, description="Agent控制服务地址")
    agent_token: str | None = Field(default=None, max_length=255, description="Agent访问令牌")
    description: str | None = Field(default=None, description="描述")


class NodeStatusUpdate(BaseModel):
    status: str = Field(..., max_length=32, description="节点状态")
