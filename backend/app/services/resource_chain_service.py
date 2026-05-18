"""
第5阶段：基础资源变更存证预留服务。

当前阶段默认不真实上链，只生成资源变更摘要并写入 chain_record。
后续接入真实区块链时，只需要在 anchor_resource_operation 中扩展远程上链调用。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chain_record import ChainRecord
from app.models.sys_user import SysUser


VOLATILE_FIELDS = {"created_at", "updated_at", "last_login_time", "last_login_at"}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items() if k not in VOLATILE_FIELDS}
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    return value


def object_to_dict(obj: Any) -> dict | None:
    """将 SQLAlchemy 模型或普通 dict 转为可 hash 的 dict。"""
    if obj is None:
        return None

    if isinstance(obj, dict):
        return _normalize_value(obj)

    table = getattr(obj, "__table__", None)

    # 关键修复：SQLAlchemy Table 对象不能用 if not table 判断
    if table is None:
        return None

    data = {}
    for col in table.columns:
        name = col.name
        if name in VOLATILE_FIELDS:
            continue

        value = getattr(obj, name, None)
        data[name] = _normalize_value(value)

    return data


def hash_dict(data: dict | None) -> str | None:
    if data is None:
        return None
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_operation_payload(
    *,
    resource_type: str,
    resource_id: int | str,
    operation_type: str,
    operator_id: int | None,
    operator_name: str | None,
    agency_id: int | None,
    before_data: dict | None,
    after_data: dict | None,
) -> dict:
    before_hash = hash_dict(before_data)
    after_hash = hash_dict(after_data)
    payload = {
        "biz_type": "resource_operation",
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "operation_type": operation_type,
        "operator_id": operator_id,
        "operator_name": operator_name,
        "agency_id": agency_id,
        "before_hash": before_hash,
        "after_hash": after_hash,
        "operation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    payload["content_hash"] = hash_dict(payload)
    return payload


def anchor_resource_operation(
    db: Session,
    *,
    resource_type: str,
    resource_id: int | str,
    operation_type: str,
    operator: SysUser | None,
    agency_id: int | None = None,
    before_data: Any = None,
    after_data: Any = None,
) -> ChainRecord:
    """
    记录资源变更存证预留记录。

    默认 RESOURCE_CHAIN_ENABLED=false，仅写 skipped 记录。
    未来真实上链时，可将 RESOURCE_CHAIN_ENABLED=true 后扩展此方法内的远程调用逻辑。
    """
    before_dict = object_to_dict(before_data)
    after_dict = object_to_dict(after_data)

    payload = build_operation_payload(
        resource_type=resource_type,
        resource_id=resource_id,
        operation_type=operation_type,
        operator_id=operator.id if operator else None,
        operator_name=(operator.real_name or operator.username) if operator else None,
        agency_id=agency_id,
        before_data=before_dict,
        after_data=after_dict,
    )

    chain_enabled = os.getenv("RESOURCE_CHAIN_ENABLED", "false").lower() == "true"
    status = "pending" if chain_enabled else "skipped"

    record = ChainRecord(
        biz_type="resource_operation",
        biz_id=f"{resource_type}:{resource_id}:{operation_type}:{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        content_hash=payload["content_hash"],
        chain_type=getattr(settings, "FISCO_CHAIN_TYPE", "fisco_bcos"),
        contract_address=getattr(settings, "FISCO_CONTRACT_ADDRESS", None),
        status=status,
        error_message=None if chain_enabled else "RESOURCE_CHAIN_ENABLED=false，当前阶段仅预留存证记录，未真实上链",
        agency_id=agency_id,
        anchor_id=payload["content_hash"],
        verify_status="unverified",
        verify_detail_json=payload,
        updated_at=datetime.now(),
    )
    db.add(record)
    db.flush()
    return record
