"""
群组生命周期日志相关 Schema。

包含：生命周期日志查询响应模型。
"""

from pydantic import BaseModel, Field
from typing import Any


# ============================================================
# 生命周期日志
# ============================================================

class LifecycleLogItem(BaseModel):
    """生命周期日志条目。"""
    id: int
    group_id: int
    event_type: str
    before_status: str | None = None
    after_status: str | None = None
    operator_user_id: int | None = None
    operator_name: str | None = None
    reason: str | None = None
    detail_json: dict[str, Any] | None = None
    created_at: str | None = None

    model_config = {"from_attributes": True}
