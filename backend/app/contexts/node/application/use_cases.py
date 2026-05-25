from datetime import datetime
from ..domain.models import NodeInfo
from ..domain.ports import NodeRepository, AccessControlPort, AuditLogPort, AgencyQueryPort, AgentPort
from ..domain.exceptions import NodeNotFound, NodeCodeAlreadyExists, NodeAgencyNotFound, InvalidNodeStatus, NoFieldsToUpdate, AgentNotConfigured
from .dtos import NodeDTO, PaginatedNodesDTO, AgentResultDTO, DeleteResultDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_dto(node: NodeInfo, agency_name: str | None = None) -> NodeDTO:
    return NodeDTO(
        id=node.id, node_code=node.node_code, node_name=node.node_name,
        agency_id=node.agency_id, agency_name=agency_name,
        node_type=node.node_type, node_capabilities=node.node_capabilities or [],
        node_role=node.node_role, service_url=node.service_url,
        endpoint=node.endpoint, internal_ip=node.internal_ip, public_ip=node.public_ip,
        health_check_url=node.health_check_url, ray_address=node.ray_address,
        anchor_service_url=node.anchor_service_url, contract_address=node.contract_address,
        status=node.status,
        last_heartbeat_at=_format_dt(node.last_heartbeat_at or node.last_heartbeat_time),
        node_load_status=node.node_load_status,
        agent_url=node.agent_url, agent_token=node.agent_token,
        last_check_at=_format_dt(node.last_check_at), last_check_result=node.last_check_result,
        activation_status=node.activation_status, activation_message=node.activation_message,
        description=node.description,
        created_at=_format_dt(node.created_at), updated_at=_format_dt(node.updated_at),
    )


class ListNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, current_user, **filters) -> PaginatedNodesDTO:
        manageable_ids = self._access_control.get_manageable_agency_ids(current_user)
        agency_id = filters.get("agency_id")
        if agency_id is not None:
            self._access_control.require_agency_in_scope(current_user, agency_id)
        nodes, total = self._repo.list_nodes(manageable_ids=manageable_ids, **filters)
        items = [_to_dto(n, self._agency.get_agency_name(n.agency_id)) for n in nodes]
        return PaginatedNodesDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetNodeDetailUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, node_id: int, current_user) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class CreateNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, payload: dict, current_user, db=None, request=None) -> NodeDTO:
        agency_id = payload.get("agency_id")
        if not self._access_control.is_platform_admin(current_user.id) and not agency_id:
            agency_id = current_user.agency_id
            payload["agency_id"] = agency_id
        self._access_control.require_agency_in_scope(current_user, agency_id)
        if not self._agency.get_agency_by_id(agency_id):
            raise NodeAgencyNotFound()
        node_code = payload.get("node_code")
        if self._repo.get_by_code(node_code):
            raise NodeCodeAlreadyExists()
        node_type = NodeInfo.normalize_node_type(payload.get("node_type"))
        capabilities = NodeInfo.normalize_capabilities(node_type, payload.get("node_capabilities"))
        endpoint = payload.get("endpoint") or payload.get("service_url")
        node = NodeInfo(
            node_code=node_code, node_name=payload.get("node_name"),
            agency_id=agency_id, node_type=node_type,
            node_capabilities=capabilities, node_role=payload.get("node_role"),
            service_url=payload.get("service_url"), endpoint=endpoint,
            internal_ip=payload.get("internal_ip"), public_ip=payload.get("public_ip"),
            health_check_url=payload.get("health_check_url"), ray_address=payload.get("ray_address"),
            anchor_service_url=payload.get("anchor_service_url"), contract_address=payload.get("contract_address"),
            agent_url=payload.get("agent_url"), agent_token=payload.get("agent_token"),
            status="registered", activation_status="not_activated", node_load_status="disabled",
            description=payload.get("description"),
        )
        node = self._repo.save(node)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_CREATE", resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="node", resource_id=node.id,
                operation_type="create", operator=current_user,
                agency_id=node.agency_id, before_data=None, after_data=node,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class UpdateNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, node_id: int, payload: dict, current_user, db=None, request=None) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        if "agency_id" in payload and payload["agency_id"] is not None:
            self._access_control.require_agency_in_scope(current_user, payload["agency_id"])
            if not self._agency.get_agency_by_id(payload["agency_id"]):
                raise NodeAgencyNotFound()
        if "node_type" in payload and payload["node_type"] is not None:
            payload["node_type"] = NodeInfo.normalize_node_type(payload["node_type"])
        if "node_capabilities" in payload:
            nt = payload.get("node_type") or node.node_type
            payload["node_capabilities"] = NodeInfo.normalize_capabilities(nt, payload.get("node_capabilities"))
        elif "node_type" in payload and payload["node_type"] is not None:
            payload["node_capabilities"] = NodeInfo.normalize_capabilities(payload["node_type"], None)
        update_fields = [
            "node_name", "agency_id", "node_type", "node_capabilities", "node_role", "service_url",
            "endpoint", "internal_ip", "public_ip", "health_check_url", "ray_address",
            "anchor_service_url", "contract_address", "agent_url", "agent_token", "description",
        ]
        changed = False
        for f in update_fields:
            if f in payload:
                setattr(node, f, payload[f])
                changed = True
        if "service_url" in payload and "endpoint" not in payload:
            node.endpoint = payload.get("service_url")
            changed = True
        if not changed:
            raise NoFieldsToUpdate()
        node.updated_at = datetime.now()
        node = self._repo.save(node)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_UPDATE", resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="node", resource_id=node.id,
                operation_type="update", operator=current_user,
                agency_id=node.agency_id, before_data=None, after_data=node,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class UpdateNodeStatusUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency

    def execute(self, node_id: int, status: str, current_user, db=None, request=None) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        try:
            node.set_status(status)
        except ValueError:
            raise InvalidNodeStatus(status)
        self._access_control.check_can_manage_node(current_user, node)
        node = self._repo.save(node)
        operation_type = (
            "NODE_ENABLE" if status == "active"
            else "NODE_DISABLE" if status == "disabled"
            else "NODE_STATUS_UPDATE"
        )
        chain_op = (
            "enable" if status == "active"
            else "disable" if status == "disabled"
            else "status_update"
        )
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type=operation_type, resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="node", resource_id=node.id,
                operation_type=chain_op, operator=current_user,
                agency_id=node.agency_id, before_data=None, after_data=node,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class DeleteNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit

    def execute(self, node_id: int, current_user, db=None, request=None) -> DeleteResultDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        self._repo.delete(node_id)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_DELETE", resource_type="node",
                resource_id=node_id, request=request,
            )
        return DeleteResultDTO(deleted=True, node_id=node_id)


class CheckNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort, agent: AgentPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency
        self._agent = agent

    def execute(self, node_id: int, current_user, db=None, request=None) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        if not node.agent_url:
            raise AgentNotConfigured()
        try:
            result = self._agent.check_status(node.agent_url, node.agent_token)
            http_ok = result.get("http_ok", True)
            agent_reachable = True
        except Exception as e:
            result = {"success": False, "error": str(e), "message": f"Agent 不可达：{e}"}
            http_ok = False
            agent_reachable = False
        node.record_check(result, agent_reachable=agent_reachable, http_ok=http_ok)
        node = self._repo.save(node)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_CHECK", resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class ActivateNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort, agent: AgentPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency
        self._agent = agent

    def execute(self, node_id: int, current_user, db=None, request=None) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        if not node.agent_url:
            raise AgentNotConfigured()
        node.start_activation()
        node = self._repo.save(node)
        try:
            result = self._agent.activate(node.agent_url, node.agent_token)
            success = bool(result.get("success", result.get("http_ok", True)))
            node.complete_activation(result, success)
        except Exception as e:
            node.fail_activation(str(e))
        node = self._repo.save(node)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_ACTIVATE", resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="node", resource_id=node.id,
                operation_type="activate", operator=current_user,
                agency_id=node.agency_id, before_data=None, after_data=node,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))


class DeactivateNodeUseCase:
    def __init__(self, repo: NodeRepository, access_control: AccessControlPort, audit: AuditLogPort, agency: AgencyQueryPort, agent: AgentPort):
        self._repo = repo
        self._access_control = access_control
        self._audit = audit
        self._agency = agency
        self._agent = agent

    def execute(self, node_id: int, current_user, db=None, request=None) -> NodeDTO:
        node = self._repo.get_by_id(node_id)
        if not node:
            raise NodeNotFound()
        self._access_control.check_can_manage_node(current_user, node)
        if not node.agent_url:
            raise AgentNotConfigured()
        try:
            result = self._agent.deactivate(node.agent_url, node.agent_token)
            success = bool(result.get("success", result.get("http_ok", True)))
            node.complete_deactivation(result, success)
        except Exception as e:
            node.fail_deactivation(str(e))
        node = self._repo.save(node)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="NODE_DEACTIVATE", resource_type="node",
                resource_id=node.id, agency_id=node.agency_id, request=request,
            )
            self._audit.anchor_resource_operation(
                db, resource_type="node", resource_id=node.id,
                operation_type="deactivate", operator=current_user,
                agency_id=node.agency_id, before_data=None, after_data=node,
            )
        return _to_dto(node, self._agency.get_agency_name(node.agency_id))
