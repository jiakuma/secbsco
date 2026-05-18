"""第5阶段：机构管理服务。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from fastapi import HTTPException, Request
from sqlalchemy import bindparam, inspect, or_, text
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.sys_user import SysUser
from app.models.node import Node
from app.services.access_control_service import write_operate_log
from app.services.resource_permission_service import (
    get_manageable_agency_ids,
    check_can_create_child_agency,
    check_can_manage_agency,
)
from app.services.resource_chain_service import anchor_resource_operation, object_to_dict


VALID_AGENCY_STATUS = {"active", "disabled"}


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _normalize_ids(values: Iterable[Any] | None) -> list[int]:
    result: list[int] = []
    for value in values or []:
        if value is None:
            continue
        if hasattr(value, "__class__") and value.__class__.__name__ == "Row":
            value = tuple(value)
        if isinstance(value, tuple):
            value = value[0] if value else None
        if value is not None:
            result.append(int(value))
    return sorted(set(result))


def _table_columns(db: Session, table_name: str) -> set[str]:
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _delete_by_values(db: Session, table_name: str, column_name: str, values: Iterable[Any] | None) -> None:
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


def _select_values_by_values(
    db: Session,
    table_name: str,
    select_column: str,
    filter_column: str,
    values: Iterable[Any] | None,
) -> list[int]:
    ids = _normalize_ids(values)
    columns = _table_columns(db, table_name)
    if not ids or select_column not in columns or filter_column not in columns:
        return []
    stmt = text(
        f"SELECT DISTINCT `{select_column}` FROM `{table_name}` "
        f"WHERE `{filter_column}` IN :values AND `{select_column}` IS NOT NULL"
    ).bindparams(bindparam("values", expanding=True))
    return _normalize_ids(db.execute(stmt, {"values": ids}).fetchall())


def _single_primary_key_column(db: Session, table_name: str) -> str | None:
    """返回单字段主键名；复合主键表只做直接删除，不做递归追踪。"""
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        return None
    pk = inspector.get_pk_constraint(table_name) or {}
    columns = pk.get("constrained_columns") or []
    return columns[0] if len(columns) == 1 else None


def _delete_fk_dependents(
    db: Session,
    parent_table: str,
    parent_column: str,
    parent_values: Iterable[Any] | None,
    skip_tables: set[str] | None = None,
    visited: set[tuple[str, str]] | None = None,
) -> None:
    """
    递归删除引用 parent_table.parent_column 的子表记录。

    用途：物理删除机构时，自动清理 dataset.agency_id、task.agency_id 等
    后续新增的直接/间接外键引用，避免只手写几张表导致 1451 外键错误。
    """
    values = _normalize_ids(parent_values)
    if not values:
        return

    skip_tables = skip_tables or set()
    visited = visited or set()
    visit_key = (parent_table, parent_column)
    if visit_key in visited:
        return
    visited.add(visit_key)

    inspector = inspect(db.bind)
    for table_name in inspector.get_table_names():
        if table_name in skip_tables:
            continue

        for fk in inspector.get_foreign_keys(table_name):
            referred_table = fk.get("referred_table")
            referred_columns = fk.get("referred_columns") or []
            constrained_columns = fk.get("constrained_columns") or []

            if referred_table != parent_table or parent_column not in referred_columns:
                continue

            idx = referred_columns.index(parent_column)
            if idx >= len(constrained_columns):
                continue

            child_fk_column = constrained_columns[idx]
            child_pk_column = _single_primary_key_column(db, table_name)

            # 若子表有单主键，先拿到子表主键并递归删除孙表。
            if child_pk_column:
                child_ids = _select_values_by_values(
                    db=db,
                    table_name=table_name,
                    select_column=child_pk_column,
                    filter_column=child_fk_column,
                    values=values,
                )
                _delete_fk_dependents(
                    db=db,
                    parent_table=table_name,
                    parent_column=child_pk_column,
                    parent_values=child_ids,
                    skip_tables=skip_tables,
                    visited=visited,
                )

            _delete_by_values(db, table_name, child_fk_column, values)


def _delete_chain_records(db: Session, resource_type: str, resource_ids: Iterable[Any] | None) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "chain_record")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `chain_record` "
        "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _delete_operate_logs(db: Session, resource_type: str, resource_ids: Iterable[Any] | None) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "sys_user_operate_log")
    if not ids:
        return
    if {"resource_type", "resource_id"}.issubset(columns):
        stmt = text(
            "DELETE FROM `sys_user_operate_log` "
            "WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
        ).bindparams(bindparam("resource_ids", expanding=True))
        db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _get_agency_and_descendant_ids(db: Session, root_agency_id: int) -> list[int]:
    """获取目标机构及所有下级机构，物理删除时不再按 status 过滤。"""
    result: list[int] = []
    visited: set[int] = set()
    queue: list[int] = [root_agency_id]

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        result.append(current_id)

        children = db.query(Agency.id).filter(Agency.parent_agency_id == current_id).all()
        queue.extend([row[0] for row in children])

    return result


def get_agency_name(db: Session, agency_id: int | None) -> str | None:
    if not agency_id:
        return None
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    return agency.agency_name if agency else None


def agency_to_dict(db: Session, agency: Agency) -> dict:
    child_count = db.query(Agency).filter(Agency.parent_agency_id == agency.id).count()
    user_count = 0
    try:
        from app.models.sys_user import SysUser
        user_count = db.query(SysUser).filter(SysUser.agency_id == agency.id).count()
    except Exception:
        user_count = 0
    node_count = db.query(Node).filter(Node.agency_id == agency.id).count()

    return {
        "id": agency.id,
        "agency_code": agency.agency_code,
        "agency_name": agency.agency_name,
        "agency_type": agency.agency_type,
        "agency_level": agency.agency_level,
        "parent_agency_id": agency.parent_agency_id,
        "parent_agency_name": get_agency_name(db, agency.parent_agency_id),
        "region_code": agency.region_code,
        "region_name": agency.region_name,
        "contact_person": agency.contact_person,
        "contact_phone": agency.contact_phone,
        "status": agency.status,
        "description": agency.description,
        "created_at": _format_dt(agency.created_at),
        "updated_at": _format_dt(agency.updated_at),
        "summary": {
            "child_count": child_count,
            "user_count": user_count,
            "node_count": node_count,
        },
    }


def list_agencies(
    db: Session,
    current_user: SysUser,
    keyword: str | None = None,
    agency_level: str | None = None,
    agency_type: str | None = None,
    status: str | None = None,
    parent_agency_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    manageable_ids = get_manageable_agency_ids(db, current_user)
    query = db.query(Agency)

    if manageable_ids is not None:
        query = query.filter(Agency.id.in_(manageable_ids))

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Agency.agency_code.like(like), Agency.agency_name.like(like)))

    if agency_level:
        query = query.filter(Agency.agency_level == agency_level)
    if agency_type:
        query = query.filter(Agency.agency_type == agency_type)
    if status:
        query = query.filter(Agency.status == status)
    if parent_agency_id is not None:
        query = query.filter(Agency.parent_agency_id == parent_agency_id)

    total = query.count()
    items = (
        query.order_by(Agency.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [agency_to_dict(db, item) for item in items],
    }


def get_agency_tree(db: Session, current_user: SysUser) -> list[dict]:
    manageable_ids = get_manageable_agency_ids(db, current_user)
    query = db.query(Agency)
    if manageable_ids is not None:
        query = query.filter(Agency.id.in_(manageable_ids))
    agencies = query.order_by(Agency.id.asc()).all()

    item_map = {
        a.id: {
            "id": a.id,
            "label": a.agency_name,
            "agency_code": a.agency_code,
            "agency_name": a.agency_name,
            "agency_level": a.agency_level,
            "agency_type": a.agency_type,
            "parent_agency_id": a.parent_agency_id,
            "status": a.status,
            "children": [],
        }
        for a in agencies
    }

    roots = []
    for agency in agencies:
        item = item_map[agency.id]
        if agency.parent_agency_id and agency.parent_agency_id in item_map:
            item_map[agency.parent_agency_id]["children"].append(item)
        else:
            roots.append(item)
    return roots


def get_agency_detail(db: Session, agency_id: int, current_user: SysUser) -> dict:
    check_can_manage_agency(db, current_user, agency_id)
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="机构不存在")
    return agency_to_dict(db, agency)


def create_agency(db: Session, payload: dict, current_user: SysUser, request: Request | None = None) -> dict:
    agency_code = payload.get("agency_code")
    if db.query(Agency).filter(Agency.agency_code == agency_code).first():
        raise HTTPException(status_code=400, detail="机构编码已存在")

    parent_agency_id = payload.get("parent_agency_id")
    agency_level = payload.get("agency_level")

    if parent_agency_id:
        parent = db.query(Agency).filter(Agency.id == parent_agency_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="上级机构不存在")

    check_can_create_child_agency(db, current_user, parent_agency_id, agency_level)

    status = payload.get("status") or "active"
    if status not in VALID_AGENCY_STATUS:
        raise HTTPException(status_code=400, detail="机构状态只能是 active 或 disabled")

    agency = Agency(
        agency_code=agency_code,
        agency_name=payload.get("agency_name"),
        agency_type=payload.get("agency_type"),
        agency_level=agency_level,
        parent_agency_id=parent_agency_id,
        region_code=payload.get("region_code"),
        region_name=payload.get("region_name"),
        contact_person=payload.get("contact_person"),
        contact_phone=payload.get("contact_phone"),
        description=payload.get("description"),
        status=status,
    )
    db.add(agency)
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="AGENCY_CREATE",
        resource_type="agency",
        resource_id=agency.id,
        agency_id=agency.id,
        request=request,
    )
    anchor_resource_operation(
        db,
        resource_type="agency",
        resource_id=agency.id,
        operation_type="create",
        operator=current_user,
        agency_id=agency.id,
        before_data=None,
        after_data=agency,
    )
    db.commit()
    db.refresh(agency)
    return agency_to_dict(db, agency)


def update_agency(db: Session, agency_id: int, payload: dict, current_user: SysUser, request: Request | None = None) -> dict:
    check_can_manage_agency(db, current_user, agency_id)
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="机构不存在")

    before = object_to_dict(agency)

    new_parent_id = payload.get("parent_agency_id", agency.parent_agency_id)
    new_level = payload.get("agency_level", agency.agency_level)

    if new_parent_id == agency_id:
        raise HTTPException(status_code=400, detail="上级机构不能是自身")

    descendant_ids = _get_agency_and_descendant_ids(db, agency_id)
    if new_parent_id in descendant_ids:
        raise HTTPException(status_code=400, detail="上级机构不能选择自身或下级机构")

    check_can_create_child_agency(db, current_user, new_parent_id, new_level)

    update_fields = [
        "agency_name", "agency_type", "agency_level", "parent_agency_id",
        "region_code", "region_name", "contact_person", "contact_phone", "description",
    ]
    changed = False
    for field in update_fields:
        if field in payload:
            setattr(agency, field, payload[field])
            changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    agency.updated_at = datetime.now()
    db.flush()

    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type="AGENCY_UPDATE",
        resource_type="agency",
        resource_id=agency.id,
        agency_id=agency.id,
        request=request,
    )
    anchor_resource_operation(
        db,
        resource_type="agency",
        resource_id=agency.id,
        operation_type="update",
        operator=current_user,
        agency_id=agency.id,
        before_data=before,
        after_data=agency,
    )
    db.commit()
    db.refresh(agency)
    return agency_to_dict(db, agency)


def set_agency_status(db: Session, agency_id: int, status: str, current_user: SysUser, request: Request | None = None) -> dict:
    if status not in {"active", "disabled"}:
        raise HTTPException(status_code=400, detail="状态只能设置为 active 或 disabled")

    check_can_manage_agency(db, current_user, agency_id)
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="机构不存在")

    before = object_to_dict(agency)
    agency.status = status
    agency.updated_at = datetime.now()
    db.flush()

    operation_type = "AGENCY_ENABLE" if status == "active" else "AGENCY_DISABLE"
    write_operate_log(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        operation_type=operation_type,
        resource_type="agency",
        resource_id=agency.id,
        agency_id=agency.id,
        request=request,
    )
    anchor_resource_operation(
        db,
        resource_type="agency",
        resource_id=agency.id,
        operation_type="enable" if status == "active" else "disable",
        operator=current_user,
        agency_id=agency.id,
        before_data=before,
        after_data=agency,
    )
    db.commit()
    db.refresh(agency)
    return agency_to_dict(db, agency)


def delete_agency(db: Session, agency_id: int, current_user: SysUser, request: Request | None = None) -> dict:
    """物理删除机构及其下级机构，同时清理用户、节点、群组关系和存证等关联数据。"""
    check_can_manage_agency(db, current_user, agency_id)
    agency = db.query(Agency).filter(Agency.id == agency_id).first()
    if not agency:
        raise HTTPException(status_code=404, detail="机构不存在")

    agency_ids = _get_agency_and_descendant_ids(db, agency_id)
    user_ids = _normalize_ids(db.query(SysUser.id).filter(SysUser.agency_id.in_(agency_ids)).all())
    node_ids = _normalize_ids(db.query(Node.id).filter(Node.agency_id.in_(agency_ids)).all())
    group_ids = sorted(set(
        _select_values_by_values(db, "group_member", "group_id", "agency_id", agency_ids)
        + _select_values_by_values(db, "group_info", "id", "agency_id", agency_ids)
        + _select_values_by_values(db, "group_info", "id", "owner_agency_id", agency_ids)
        + _select_values_by_values(db, "group_info", "id", "creator_agency_id", agency_ids)
    ))

    try:
        # 先清理链上/日志/关系类数据，避免外键阻塞主表删除。
        _delete_chain_records(db, "agency", agency_ids)
        _delete_chain_records(db, "user", user_ids)
        _delete_chain_records(db, "node", node_ids)
        _delete_operate_logs(db, "agency", agency_ids)
        _delete_operate_logs(db, "user", user_ids)
        _delete_operate_logs(db, "node", node_ids)
        _delete_by_values(db, "chain_record", "agency_id", agency_ids)
        _delete_by_values(db, "sys_user_operate_log", "agency_id", agency_ids)

        _delete_by_values(db, "sys_user_role_binding", "user_id", user_ids)
        _delete_by_values(db, "sys_user_group", "user_id", user_ids)
        _delete_by_values(db, "sys_user_group", "agency_id", agency_ids)

        _delete_by_values(db, "group_node", "node_id", node_ids)
        _delete_by_values(db, "group_node", "agency_id", agency_ids)
        _delete_by_values(db, "group_node", "group_id", group_ids)
        _delete_by_values(db, "group_member", "agency_id", agency_ids)
        _delete_by_values(db, "group_lifecycle_log", "agency_id", agency_ids)
        _delete_by_values(db, "group_lifecycle_log", "group_id", group_ids)

        # 兜底清理所有通过外键直接或间接引用 agency.id 的业务表。
        # 当前日志中的 dataset.agency_id -> agency.id 就会在这里被清理。
        _delete_fk_dependents(db, "agency", "id", agency_ids, skip_tables={"agency"})

        db.query(Node).filter(Node.id.in_(node_ids)).delete(synchronize_session=False)
        db.query(SysUser).filter(SysUser.id.in_(user_ids)).delete(synchronize_session=False)

        for delete_id in reversed(agency_ids):
            target = db.query(Agency).filter(Agency.id == delete_id).first()
            if target:
                db.delete(target)

        db.commit()
        return {
            "deleted": True,
            "agency_id": agency_id,
            "deleted_agency_ids": agency_ids,
            "deleted_user_count": len(user_ids),
            "deleted_node_count": len(node_ids),
        }
    except Exception:
        db.rollback()
        raise
