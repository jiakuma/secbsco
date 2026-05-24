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

VALID_NODE_TYPES = {
    "integrated_node",
    "service_node",
    "data_node",
    "compute_node",
    "blockchain_node",
    "gateway_node",
}
VALID_NODE_CAPABILITIES = {"data", "compute", "service", "chain"}
NODE_TYPE_ALIASES = {
    "chain_node": "blockchain_node",
}
DEFAULT_CAPABILITIES_BY_TYPE = {
    "integrated_node": ["data", "compute", "service", "chain"],
    "data_node": ["data"],
    "compute_node": ["compute"],
    "service_node": ["service"],
    "blockchain_node": ["chain"],
    "gateway_node": ["service"],
}


def _normalize_node_type(node_type: str | None) -> str:
    """规范节点类型，兼容历史 chain_node 写法。"""
    value = (node_type or "integrated_node").strip()
    value = NODE_TYPE_ALIASES.get(value, value)
    if value not in VALID_NODE_TYPES:
        raise HTTPException(status_code=400, detail="节点类型不合法")
    return value


def _normalize_capabilities(node_type: str, capabilities) -> list[str]:
    """规范节点能力。一个节点可同时具备数据、计算、服务、存证能力。"""
    if capabilities is None or capabilities == "":
        raw_values = DEFAULT_CAPABILITIES_BY_TYPE.get(node_type, [])
    elif isinstance(capabilities, str):
        raw_values = [item.strip() for item in capabilities.split(",") if item.strip()]
    elif isinstance(capabilities, (list, tuple, set)):
        raw_values = list(capabilities)
    else:
        raise HTTPException(status_code=400, detail="节点能力格式不合法")

    normalized: list[str] = []
    for item in raw_values:
        value = str(item).strip()
        if not value:
            continue
        if value not in VALID_NODE_CAPABILITIES:
            raise HTTPException(status_code=400, detail=f"节点能力不合法：{value}")
        if value not in normalized:
            normalized.append(value)

    if not normalized:
        normalized = DEFAULT_CAPABILITIES_BY_TYPE.get(node_type, [])

    if not normalized:
        raise HTTPException(status_code=400, detail="节点能力不能为空")

    return normalized


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _normalize_ids(values) -> list[int]:
    result: list[int] = []
    for value in values or []:
        if value is None:
            continue
        # SQLAlchemy 2.x Row 对象支持 _mapping；普通 tuple/list 取第一个元素。
        if hasattr(value, "_mapping"):
            row_values = list(value._mapping.values())
            value = row_values[0] if row_values else None
        elif isinstance(value, (tuple, list)):
            value = value[0] if value else None
        if value is None:
            continue
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
            "node_capabilities": node.node_capabilities or [],
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
            "agent_url": node.agent_url,
            "agent_token": node.agent_token,
            "last_check_at": _format_dt(node.last_check_at),
            "last_check_result": node.last_check_result,
            "activation_status": node.activation_status,
            "activation_message": node.activation_message,
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

        status = "registered"
        node_type = _normalize_node_type(payload.get("node_type"))
        node_capabilities = _normalize_capabilities(node_type, payload.get("node_capabilities"))

        endpoint = payload.get("endpoint") or payload.get("service_url")
        node = Node(
            node_code=node_code,
            node_name=payload.get("node_name"),
            agency_id=agency_id,
            node_type=node_type,
            node_capabilities=node_capabilities,
            node_role=payload.get("node_role"),
            service_url=payload.get("service_url"),
            endpoint=endpoint,
            internal_ip=payload.get("internal_ip"),
            public_ip=payload.get("public_ip"),
            health_check_url=payload.get("health_check_url"),
            ray_address=payload.get("ray_address"),
            anchor_service_url=payload.get("anchor_service_url"),
            contract_address=payload.get("contract_address"),
            agent_url=payload.get("agent_url"),
            agent_token=payload.get("agent_token"),
            status=status,
            activation_status="not_activated",
            node_load_status="disabled",
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

        if "node_type" in payload and payload["node_type"] is not None:
            payload["node_type"] = _normalize_node_type(payload["node_type"])

        if "node_capabilities" in payload:
            node_type_for_capabilities = payload.get("node_type") or node.node_type
            payload["node_capabilities"] = _normalize_capabilities(
                node_type_for_capabilities,
                payload.get("node_capabilities"),
            )
        elif "node_type" in payload and payload["node_type"] is not None:
            # 类型变更但前端未传能力时，按新类型默认能力补齐。
            payload["node_capabilities"] = _normalize_capabilities(payload["node_type"], None)

        update_fields = [
            "node_name", "agency_id", "node_type", "node_capabilities", "node_role", "service_url",
            "endpoint", "internal_ip", "public_ip", "health_check_url", "ray_address",
            "anchor_service_url", "contract_address", "agent_url", "agent_token", "description",
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
    @staticmethod
    def _parse_agent_response(resp) -> dict:
        """解析 node-agent 返回，兼容 JSON 和文本响应。"""
        content_type = resp.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                data = resp.json()
                return data if isinstance(data, dict) else {"data": data}
            except Exception:
                return {"raw": resp.text}
        return {"raw": resp.text}

    @staticmethod
    def _build_agent_headers(node: Node) -> dict:
        """构造调用 node-agent 的请求头。"""
        headers = {}
        if node.agent_token:
            headers["Authorization"] = f"Bearer {node.agent_token}"
        return headers

    @staticmethod
    def check_node(db: Session, node: Node, current_user: SysUser, request: Request | None = None) -> dict:
        """
        检测节点 Agent 状态。

        注意：
        - 检测成功只更新 last_check_at / last_check_result，不把 active 节点降级为 registered。
        - Agent 不可达时才将节点状态置为 offline。
        """
        import requests

        check_can_manage_node(db, current_user, node)

        if not node.agent_url:
            raise HTTPException(status_code=400, detail="节点未配置Agent地址")

        headers = NodeService._build_agent_headers(node)

        try:
            resp = requests.get(
                f"{node.agent_url.rstrip('/')}/status",
                headers=headers,
                timeout=15,
            )
            check_result = NodeService._parse_agent_response(resp)

            node.last_check_at = datetime.now()
            node.last_check_result = check_result
            node.activation_message = check_result.get("message", "节点检测完成")

            # 检测成功说明 Agent 可达。如果之前是 offline / failed，可回到 registered；
            # 但不要把 active / disabled 这类业务状态覆盖掉。
            if resp.status_code == 200:
                if node.status in {"offline", "failed", "checking"}:
                    node.status = "registered"
            else:
                node.status = "failed"
                node.activation_message = check_result.get("message", f"节点检测失败，HTTP {resp.status_code}")

            node.updated_at = datetime.now()

        except Exception as e:
            node.last_check_at = datetime.now()
            node.last_check_result = {
                "success": False,
                "error": str(e),
                "message": f"Agent 不可达：{e}",
            }
            node.status = "offline"
            node.activation_message = f"Agent 不可达：{e}"
            node.updated_at = datetime.now()

        db.flush()
        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type="NODE_CHECK",
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        db.commit()
        db.refresh(node)
        return NodeService.build_node_info(node, db)

    @staticmethod
    def activate_node(db: Session, node: Node, current_user: SysUser, request: Request | None = None) -> dict:
        """
        激活节点。

        关键调整：
        - 不再只看 HTTP 200，而是同时判断 node-agent 返回的 success 字段。
        - 保存完整 Agent 返回到 last_check_result，便于前端详情查看 steps/status。
        - activation_message 保存 Agent 返回的详细 message。
        - 超时时间加长，避免启动 FISCO / Ray / SecretFlow 时还没完成就超时。
        """
        import requests

        check_can_manage_node(db, current_user, node)

        if not node.agent_url:
            raise HTTPException(status_code=400, detail="节点未配置Agent地址")

        before = object_to_dict(node)

        node.status = "checking"
        node.activation_status = "activating"
        node.activation_message = "正在调用节点 Agent 执行激活流程..."
        node.updated_at = datetime.now()
        db.flush()

        headers = NodeService._build_agent_headers(node)

        try:
            resp = requests.post(
                f"{node.agent_url.rstrip('/')}/activate",
                headers=headers,
                timeout=180,
            )
            result = NodeService._parse_agent_response(resp)

            # 记录完整激活结果，里面应包含 message / summary / steps / status。
            node.last_check_at = datetime.now()
            node.last_check_result = result

            agent_success = bool(result.get("success", resp.status_code == 200))

            if resp.status_code == 200 and agent_success:
                node.status = "active"
                node.activation_status = "activated"
                node.activation_message = result.get("message", "节点激活成功")
                node.node_load_status = "idle"
            else:
                node.status = "failed"
                node.activation_status = "activation_failed"
                node.activation_message = (
                    result.get("message")
                    or result.get("error")
                    or f"节点激活失败，HTTP {resp.status_code}"
                )
                node.node_load_status = "offline"

        except Exception as e:
            node.status = "failed"
            node.activation_status = "activation_failed"
            node.activation_message = f"节点激活失败：{e}"
            node.last_check_at = datetime.now()
            node.last_check_result = {
                "success": False,
                "error": str(e),
                "message": f"节点激活失败：{e}",
            }
            node.node_load_status = "offline"

        node.updated_at = datetime.now()
        db.flush()

        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type="NODE_ACTIVATE",
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        anchor_resource_operation(
            db,
            resource_type="node",
            resource_id=node.id,
            operation_type="activate",
            operator=current_user,
            agency_id=node.agency_id,
            before_data=before,
            after_data=node,
        )
        db.commit()
        db.refresh(node)
        return NodeService.build_node_info(node, db)

    @staticmethod
    def deactivate_node(db: Session, node: Node, current_user: SysUser, request: Request | None = None) -> dict:
        """
        停用节点。

        当前阶段停用不关云服务器，也不强杀底层服务；
        主要把平台侧状态设置为 disabled，使节点不可调度。
        """
        import requests

        check_can_manage_node(db, current_user, node)

        if not node.agent_url:
            raise HTTPException(status_code=400, detail="节点未配置Agent地址")

        before = object_to_dict(node)
        headers = NodeService._build_agent_headers(node)

        try:
            resp = requests.post(
                f"{node.agent_url.rstrip('/')}/deactivate",
                headers=headers,
                timeout=60,
            )
            result = NodeService._parse_agent_response(resp)

            node.last_check_at = datetime.now()
            node.last_check_result = result

            agent_success = bool(result.get("success", resp.status_code == 200))

            if resp.status_code == 200 and agent_success:
                node.status = "disabled"
                node.activation_status = "not_activated"
                node.activation_message = result.get("message", "节点已停用")
                node.node_load_status = "disabled"
            else:
                node.activation_message = (
                    result.get("message")
                    or result.get("error")
                    or f"节点停用失败，HTTP {resp.status_code}"
                )

        except Exception as e:
            node.activation_message = f"节点停用失败：{e}"
            node.last_check_at = datetime.now()
            node.last_check_result = {
                "success": False,
                "error": str(e),
                "message": f"节点停用失败：{e}",
            }

        node.updated_at = datetime.now()
        db.flush()

        write_operate_log(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            operation_type="NODE_DEACTIVATE",
            resource_type="node",
            resource_id=node.id,
            agency_id=node.agency_id,
            request=request,
        )
        anchor_resource_operation(
            db,
            resource_type="node",
            resource_id=node.id,
            operation_type="deactivate",
            operator=current_user,
            agency_id=node.agency_id,
            before_data=before,
            after_data=node,
        )
        db.commit()
        db.refresh(node)
        return NodeService.build_node_info(node, db)
