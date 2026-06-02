from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.node import Node as NodeORM
from ..domain.models import NodeInfo
from ..domain.ports import NodeRepository, AccessControlPort, AuditLogPort, AgencyQueryPort, AgentPort


def _to_domain(orm: NodeORM) -> NodeInfo:
    return NodeInfo(
        id=orm.id, node_code=orm.node_code, node_name=orm.node_name,
        agency_id=orm.agency_id, node_type=orm.node_type,
        node_role=orm.node_role, node_capabilities=orm.node_capabilities or [],
        service_url=orm.service_url, internal_ip=orm.internal_ip,
        public_ip=orm.public_ip, endpoint=orm.endpoint,
        health_check_url=orm.health_check_url, ray_address=orm.ray_address,
        chain_type=orm.chain_type, chain_node_id=orm.chain_node_id,
        rpc_endpoint=orm.rpc_endpoint, p2p_endpoint=orm.p2p_endpoint,
        anchor_service_url=orm.anchor_service_url, contract_address=orm.contract_address,
        cert_id=orm.cert_id, status=orm.status,
        last_heartbeat_at=orm.last_heartbeat_at, last_heartbeat_time=orm.last_heartbeat_time,
        agent_url=orm.agent_url, agent_token=orm.agent_token,
        last_check_at=orm.last_check_at, last_check_result=orm.last_check_result,
        activation_status=orm.activation_status, activation_message=orm.activation_message,
        cpu_total=orm.cpu_total, memory_total=orm.memory_total, gpu_total=orm.gpu_total,
        max_concurrent_tasks=orm.max_concurrent_tasks, current_running_tasks=orm.current_running_tasks,
        node_load_status=orm.node_load_status, resource_desc_json=orm.resource_desc_json,
        description=orm.description, created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _apply_to_orm(orm: NodeORM, node: NodeInfo) -> None:
    simple_fields = [
        "node_code", "node_name", "agency_id", "node_type", "node_role",
        "node_capabilities", "service_url", "internal_ip", "public_ip", "endpoint",
        "health_check_url", "ray_address", "chain_type", "chain_node_id",
        "rpc_endpoint", "p2p_endpoint", "anchor_service_url", "contract_address",
        "cert_id", "status", "last_heartbeat_at", "last_heartbeat_time",
        "agent_url", "agent_token", "last_check_at", "last_check_result",
        "activation_status", "activation_message",
        "cpu_total", "memory_total", "gpu_total",
        "max_concurrent_tasks", "current_running_tasks",
        "node_load_status", "resource_desc_json", "description",
    ]
    for attr in simple_fields:
        setattr(orm, attr, getattr(node, attr))
    if node.updated_at:
        orm.updated_at = node.updated_at


class SQLAlchemyNodeRepository(NodeRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, node_id: int) -> NodeInfo | None:
        orm = self._db.query(NodeORM).filter(NodeORM.id == node_id).first()
        return _to_domain(orm) if orm else None

    def get_by_code(self, node_code: str) -> NodeInfo | None:
        orm = self._db.query(NodeORM).filter(NodeORM.node_code == node_code).first()
        return _to_domain(orm) if orm else None

    def list_nodes(self, *, manageable_ids=None, keyword=None, agency_id=None, status=None, node_type=None, page=1, page_size=10) -> tuple[list[NodeInfo], int]:
        query = self._db.query(NodeORM)
        if manageable_ids is not None:
            query = query.filter(NodeORM.agency_id.in_(manageable_ids))
        if agency_id is not None:
            query = query.filter(NodeORM.agency_id == agency_id)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(NodeORM.node_code.like(like), NodeORM.node_name.like(like)))
        if status:
            query = query.filter(NodeORM.status == status)
        else:
            query = query.filter(NodeORM.status != "archived")
        if node_type:
            query = query.filter(NodeORM.node_type == node_type)
        total = query.count()
        items = query.order_by(NodeORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_to_domain(i) for i in items], total

    def save(self, node: NodeInfo) -> NodeInfo:
        if node.id is not None:
            orm = self._db.query(NodeORM).filter(NodeORM.id == node.id).first()
            if orm:
                _apply_to_orm(orm, node)
                self._db.flush()
                self._db.refresh(orm)
                return _to_domain(orm)
        orm = NodeORM(
            node_code=node.node_code, node_name=node.node_name,
            agency_id=node.agency_id, node_type=node.node_type,
            node_capabilities=node.node_capabilities, node_role=node.node_role,
            service_url=node.service_url, endpoint=node.endpoint,
            internal_ip=node.internal_ip, public_ip=node.public_ip,
            health_check_url=node.health_check_url, ray_address=node.ray_address,
            anchor_service_url=node.anchor_service_url, contract_address=node.contract_address,
            agent_url=node.agent_url, agent_token=node.agent_token,
            status=node.status, activation_status=node.activation_status,
            node_load_status=node.node_load_status, description=node.description,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _to_domain(orm)

    def delete(self, node_id: int) -> None:
        from sqlalchemy import bindparam, inspect, text
        node = self._db.query(NodeORM).filter(NodeORM.id == node_id).first()
        if not node:
            return
        ids = [node_id]
        inspector = inspect(self._db.bind)
        for table_name, column_name in [("chain_record", "resource_id"), ("sys_user_operate_log", "resource_id"), ("group_node", "node_id")]:
            if not inspector.has_table(table_name):
                continue
            cols = {c["name"] for c in inspector.get_columns(table_name)}
            if column_name not in cols:
                continue
            if table_name == "chain_record" and "resource_type" in cols:
                stmt = text("DELETE FROM `chain_record` WHERE `resource_type` = :rt AND `resource_id` IN :ids").bindparams(bindparam("ids", expanding=True))
                self._db.execute(stmt, {"rt": "node", "ids": ids})
            elif table_name == "sys_user_operate_log" and "resource_type" in cols:
                stmt = text("DELETE FROM `sys_user_operate_log` WHERE `resource_type` = :rt AND `resource_id` IN :ids").bindparams(bindparam("ids", expanding=True))
                self._db.execute(stmt, {"rt": "node", "ids": ids})
            else:
                stmt = text(f"DELETE FROM `{table_name}` WHERE `{column_name}` IN :ids").bindparams(bindparam("ids", expanding=True))
                self._db.execute(stmt, {"ids": ids})
        self._db.delete(node)
        self._db.flush()


class BridgeAccessControlPort(AccessControlPort):
    def __init__(self, db: Session):
        self._db = db

    def get_manageable_agency_ids(self, current_user) -> list[int] | None:
        from app.contexts.shared.resource_permission_service import get_manageable_agency_ids
        return get_manageable_agency_ids(self._db, current_user)

    def require_agency_in_scope(self, current_user, agency_id: int) -> None:
        from app.contexts.shared.resource_permission_service import require_agency_in_scope
        require_agency_in_scope(self._db, current_user, agency_id)

    def check_can_manage_node(self, current_user, node) -> None:
        from app.contexts.shared.resource_permission_service import check_can_manage_node
        from app.models.node import Node as NodeORM
        if isinstance(node, NodeInfo):
            orm = self._db.query(NodeORM).filter(NodeORM.id == node.id).first()
            check_can_manage_node(self._db, current_user, orm)
        else:
            check_can_manage_node(self._db, current_user, node)

    def is_platform_admin(self, user_id: int) -> bool:
        from app.contexts.shared.access_control_service import is_platform_admin
        return is_platform_admin(self._db, user_id)


class BridgeAuditLogPort(AuditLogPort):
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None:
        from app.contexts.shared.access_control_service import write_operate_log
        write_operate_log(db=db, user_id=user_id, username=username, operation_type=operation_type,
                          resource_type=resource_type, resource_id=resource_id,
                          agency_id=agency_id, group_id=group_id, request=request)

    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None):
        from app.contexts.shared.resource_chain_service import anchor_resource_operation
        return anchor_resource_operation(db, resource_type=resource_type, resource_id=resource_id,
                                        operation_type=operation_type, operator=operator,
                                        agency_id=agency_id, before_data=before_data, after_data=after_data)


class BridgeAgencyQueryPort(AgencyQueryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_agency_by_id(self, agency_id: int | None):
        if not agency_id:
            return None
        from app.models.agency import Agency
        return self._db.query(Agency).filter(Agency.id == agency_id).first()

    def get_agency_name(self, agency_id: int | None) -> str | None:
        agency = self.get_agency_by_id(agency_id)
        return agency.agency_name if agency else None


class BridgeAgentPort(AgentPort):
    def check_status(self, agent_url: str, agent_token: str | None) -> dict:
        import requests
        headers = {}
        if agent_token:
            headers["Authorization"] = f"Bearer {agent_token}"
        resp = requests.get(f"{agent_url.rstrip('/')}/status", headers=headers, timeout=15)
        result = self._parse_response(resp)
        result["http_ok"] = resp.status_code == 200
        return result

    def activate(self, agent_url: str, agent_token: str | None) -> dict:
        import requests
        headers = {}
        if agent_token:
            headers["Authorization"] = f"Bearer {agent_token}"
        resp = requests.post(f"{agent_url.rstrip('/')}/activate", headers=headers, timeout=180)
        result = self._parse_response(resp)
        result["http_ok"] = resp.status_code == 200
        return result

    def deactivate(self, agent_url: str, agent_token: str | None) -> dict:
        import requests
        headers = {}
        if agent_token:
            headers["Authorization"] = f"Bearer {agent_token}"
        resp = requests.post(f"{agent_url.rstrip('/')}/deactivate", headers=headers, timeout=60)
        result = self._parse_response(resp)
        result["http_ok"] = resp.status_code == 200
        return result

    @staticmethod
    def _parse_response(resp) -> dict:
        content_type = resp.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                data = resp.json()
                return data if isinstance(data, dict) else {"data": data}
            except Exception:
                return {"raw": resp.text}
        return {"raw": resp.text}
