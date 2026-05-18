"""
群组相关 Pydantic Schema。

包含：群组创建、更新、审批、成员管理、用户授权、节点授权等请求/响应模型。
"""

from pydantic import BaseModel, Field


# ============================================================
# 创建群组
# ============================================================

class GroupCreate(BaseModel):
    """创建群组请求体。"""
    group_code: str = Field(..., max_length=64, description="群组编码，唯一")
    group_name: str = Field(..., max_length=128, description="群组名称")
    group_level: str = Field(default="city", max_length=32, description="群组层级: county/city/province/national")
    region_code: str = Field(default=None, max_length=64, description="区域编码")
    region_name: str = Field(default=None, max_length=128, description="区域名称")
    lead_agency_id: int = Field(..., description="牵头机构 ID")
    member_agency_ids: list[int] = Field(default_factory=list, description="成员机构 ID 列表")
    description: str = Field(default=None, description="群组描述")


# ============================================================
# 更新群组
# ============================================================

class GroupUpdate(BaseModel):
    """更新群组基础信息请求体。"""
    group_name: str = Field(default=None, max_length=128, description="群组名称")
    group_level: str = Field(default=None, max_length=32, description="群组层级")
    region_code: str = Field(default=None, max_length=64, description="区域编码")
    region_name: str = Field(default=None, max_length=128, description="区域名称")
    description: str = Field(default=None, description="群组描述")


# ============================================================
# 审批群组
# ============================================================

class GroupApprove(BaseModel):
    """审批通过群组请求体。"""
    remark: str = Field(default="审批通过", description="审批备注")


class GroupReject(BaseModel):
    """驳回群组请求体。"""
    reason: str = Field(..., min_length=1, description="驳回原因")


# ============================================================
# 添加成员机构
# ============================================================

class AddGroupMember(BaseModel):
    """添加成员机构请求体。"""
    agency_id: int = Field(..., description="机构 ID")
    member_type: str = Field(default="participant", description="成员角色: participant/data_provider/compute_provider/observer")
    remark: str = Field(default="", description="备注")


# ============================================================
# 添加群组用户
# ============================================================

class AddGroupUser(BaseModel):
    """添加群组用户请求体。"""
    user_id: int = Field(..., description="用户 ID")
    role_code: str = Field(default="user", description="群组角色: admin/user/governor")
    remark: str = Field(default="", description="备注")


class UpdateGroupUserRole(BaseModel):
    """修改群组用户角色请求体。"""
    role_code: str = Field(..., description="新角色: admin/user/governor")


# ============================================================
# 添加群组节点
# ============================================================

class AddGroupNode(BaseModel):
    """授权节点给群组请求体。"""
    node_id: int = Field(..., description="节点 ID")
    remark: str = Field(default="", description="备注")
