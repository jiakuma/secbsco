"""第5阶段：节点管理服务。"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy import bindparam, inspect, or_, text
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.node import Node
from app.models.sys_user import SysUser
from app.services.access_control_service import write_operate_log, is_platform_admin
from app.services.resource_permission_service import (
    get_manageable_agency_ids,
    require_agency_in_scope,
    check_can_manage_node,
)
from app.services.resource_chain_service import anchor_resource_operation, object_to_dict


VALID_NODE_STATUS = {"registered", "checking", "active", "offline", "disabled", "failed"}


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _normalize_ids(values) -> list[int]:
    result: list[int] = []
    for value in values or []:
        if value is None:
            continue
        if isinstance(value, tuple):
            value = value[0]
        result.append(int(value))
    return sorted(set(result))


def _table_columns(db: Session, table_name: str) -> set[str]:
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _delete_by_values(db: Session, table_name: str, column_name: str, values) -> None:
    ids = _normalize_ids(values)
    if not ids:
        return
    columns = _table_columns(db, table_name)
    if column_name not in columns:
        return
    stmt = text(f"DELETE FROM `{table_name}` WHERE `{column_name}` IN :values").bindparams(
        bindparam("values", expanding=True)
    )
    db.execute(stmt, {"values": ids})


def _delete_chain_records(db: Session, resource_type: str, resource_ids) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "chain_record")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `chain_record` "
        "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _delete_operate_logs(db: Session, resource_type: str, resource_ids) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "sys_user_operate_log")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `sys_user_operate_log` "
        "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


class NodeService:
    @staticmethod
    def get_agency_by_id(db: Session, agency_id: int | None) -> Agency | None:
        if not agency_id:
            return None
        return db.query(Agency).filter(Agency.id == agency_id).first()

    @staticmethod
    def get_node_by_id(db: Session, node_id: int) -> Node | None:
        return db.query(Node).filter(Node.id == node_id).first()

    @staticmethod
    def get_node_by_code(db: Session, node_code: str) -> Node | None:
        return db.query(Node).filter(Node.node_code == node_code).first()

    @staticmethod
    def build_node_info(node: Node, db: Session | None = None) -> dict:
        agency_name = None
        if db is not None and node.agency_id:
            agency = db.query(Agency).filter(Agency.id == node.agency_id).first()
            agency_name = agency.agency_name if agency else None

        return {
            "id": node.id,
            "node_code": node.node_code,
            "node_name": node.node_name,
            "agency_id": node.agency_id,
            "agency_name": agency_name,
            "node_type": node.node_type,
            "node_role": node.node_role,
            "service_url": node.service_url,
            "endpoint": node.endpoint,
            "internal_ip": node.internal_ip,
            "public_ip": node.public_ip,
            "health_check_url": node.health_check_url,
            "ray_address": node.ray_address,
            "anchor_service_url": node.anchor_service_url,
            "contract_address": node.contract_address,
            "status": node.status,
            "last_heartbeat_at": _format_dt(node.last_heartbeat_at or node.last_heartbeat_time),
            "node_load_status": node.node_load_status,
            "description": node.description,
            "created_at": _format_dt(node.created_at),
            "updated_at": _format_dt(node.updated_at),
        }

    @staticmethod
    def list_nodes(
        db: Session,
        current_user: SysUser,
        keyword: str | None = None,
        agency_id: int | None = None,
        status: str | None = None,
        node_type: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[Node]]:
        manageable_ids = get_manageable_agency_ids(db, current_user)
        query = db.query(Node)

        if manageable_ids is not None:
            query = query.filter(Node.agency_id.in_(manageable_ids))

        if agency_id is not None:
            require_agency_in_scope(db, current_user, agency_id)
            query = query.filter(Node.agency_id == agency_id)

        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Node.node_code.like(like), Node.node_name.like(like)))

        if status:
            query = query.filter(Node.status == status)
        else:
            query = query.filter(Node.status != "archived")
        if node_type:
            query = query.filter(Node.node_type == node_type)

        total = query.count()
        items = (
            query.order_by(Node.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, items

    @staticmethod
    def create_node(db: Session, payload: dict, current_user: SysUser, request: Request | None = None) -> Node:
        agency_id = payload.get("agency_id")

        # 机构管理员新增节点时，如果前端未传所属机构，默认归属当前登录用户所属机构。
        if not is_platform_admin(db, current_user.id) and not agency_id:
            agency_id = current_user.agency_id
            payload["agency_id"] = agency_id

        require_agency_in_scope(db, current_user, agency_id)

        agency = NodeService.get_agency_by_id(db, agency_id)
        if not agency:
            raise HTTPException(status_code=404, detail="所属机构不存在")

        node_code = payload.get("node_code")
        if NodeService.get_node_by_code(db, node_code):
            raise HTTPException(status_code=400, detail="节点编码已存在")

        status = payload.get("status") or "active"
        if status not in VALID_NODE_STATUS:
            raise HTTPException(status_code=400, detail="节点状态不合法")

        endpoint = payload.get("endpoint") or payload.get("service_url")
        node = Node(
            node_code=node_code,
            node_name=payload.get("node_name"),
            agency_id=agency_id,
            node_type=payload.get("node_type") or "compute_node",
            node_role=payload.get("node_role"),
            service_url=payload.get("service_url"),
            endpoint=endpoint,
            internal_ip=payload.get("internal_ip"),
            public_ip=payload.get("public_ip"),
            health_check_url=payload.get("health_check_url"),
            ray_address=payload.get("ray_address"),
            anchor_service_url=payload.get("anchor_service_url"),
            contract_address=payload.get("contract_address"),
            status=status,
            node_load_status="idle" if status == "active" else "disabled",
            description=payload.get("description"),
        )
        db.add(node)
        db.flush()

        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type="NODE_CREATE",
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        anchor_resource_operation(
            db,
            resource_type="node",
            resource_id=node.id,
            operation_type="create",
            operator=current_user,
            agency_id=node.agency_id,
            before_data=None,
            after_data=node,
        )
        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def update_node(db: Session, node: Node, payload: dict, current_user: SysUser, request: Request | None = None) -> Node:
        check_can_manage_node(db, current_user, node)
        before = object_to_dict(node)

        if "agency_id" in payload and payload["agency_id"] is not None:
            require_agency_in_scope(db, current_user, payload["agency_id"])
            if not NodeService.get_agency_by_id(db, payload["agency_id"]):
                raise HTTPException(status_code=404, detail="所属机构不存在")

        update_fields = [
            "node_name", "agency_id", "node_type", "node_role", "service_url",
            "endpoint", "internal_ip", "public_ip", "health_check_url", "ray_address",
            "anchor_service_url", "contract_address", "description",
        ]
        changed = False
        for field in update_fields:
            if field in payload:
                setattr(node, field, payload[field])
                changed = True

        if "service_url" in payload and "endpoint" not in payload:
            node.endpoint = payload.get("service_url")
            changed = True

        if not changed:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        node.updated_at = datetime.now()
        db.flush()

        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type="NODE_UPDATE",
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        anchor_resource_operation(
            db,
            resource_type="node",
            resource_id=node.id,
            operation_type="update",
            operator=current_user,
            agency_id=node.agency_id,
            before_data=before,
            after_data=node,
        )
        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def update_node_status(db: Session, node: Node, status: str, current_user: SysUser, request: Request | None = None) -> Node:
        if status not in VALID_NODE_STATUS:
            raise HTTPException(status_code=400, detail="节点状态不合法")

        check_can_manage_node(db, current_user, node)
        before = object_to_dict(node)

        node.status = status
        node.node_load_status = "disabled" if status == "disabled" else ("offline" if status == "offline" else "idle")
        node.updated_at = datetime.now()
        db.flush()

        operation_type = (
            "NODE_ENABLE" if status == "active"
            else "NODE_DISABLE" if status == "disabled"
            else "NODE_STATUS_UPDATE"
        )
        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type=operation_type,
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        anchor_resource_operation(
            db,
            resource_type="node",
            resource_id=node.id,
            operation_type=(
                "enable" if status == "active"
                else "disable" if status == "disabled"
                else "status_update"
            ),
            operator=current_user,
            agency_id=node.agency_id,
            before_data=before,
            after_data=node,
        )
        db.commit()
        db.refresh(node)
        return node

    @staticmethod
    def delete_node(db: Session, node: Node, current_user: SysUser, request: Request | None = None) -> dict:
        """物理删除节点，并清理 group_node、操作日志和存证记录。"""
        check_can_manage_node(db, current_user, node)
        node_id = node.id

        try:
            _delete_chain_records(db, "node", [node_id])
            _delete_operate_logs(db, "node", [node_id])
            _delete_by_values(db, "group_node", "node_id", [node_id])

            db.delete(node)
            db.commit()
            return {"deleted": True, "node_id": node_id}
        except Exception:
            db.rollback()
            raise

