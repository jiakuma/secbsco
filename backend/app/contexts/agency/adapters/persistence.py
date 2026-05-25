from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import bindparam, inspect, or_, text
from sqlalchemy.orm import Session

from app.models.agency import Agency as AgencyORM
from app.models.sys_user import SysUser
from app.models.node import Node
from ..domain.models import Agency
from ..domain.ports import AgencyRepository


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
    db: Session, table_name: str, select_column: str, filter_column: str, values: Iterable[Any] | None,
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
    inspector = inspect(db.bind)
    if not inspector.has_table(table_name):
        return None
    pk = inspector.get_pk_constraint(table_name) or {}
    columns = pk.get("constrained_columns") or []
    return columns[0] if len(columns) == 1 else None


def _delete_fk_dependents(
    db: Session, parent_table: str, parent_column: str, parent_values: Iterable[Any] | None,
    skip_tables: set[str] | None = None, visited: set[tuple[str, str]] | None = None,
) -> None:
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
            if child_pk_column:
                child_ids = _select_values_by_values(db, table_name, child_pk_column, child_fk_column, values)
                _delete_fk_dependents(db, table_name, child_pk_column, child_ids, skip_tables, visited)
            _delete_by_values(db, table_name, child_fk_column, values)


def _delete_chain_records(db: Session, resource_type: str, resource_ids: Iterable[Any] | None) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "chain_record")
    if not ids or not {"resource_type", "resource_id"}.issubset(columns):
        return
    stmt = text(
        "DELETE FROM `chain_record` WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
    ).bindparams(bindparam("resource_ids", expanding=True))
    db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _delete_operate_logs(db: Session, resource_type: str, resource_ids: Iterable[Any] | None) -> None:
    ids = _normalize_ids(resource_ids)
    columns = _table_columns(db, "sys_user_operate_log")
    if not ids:
        return
    if {"resource_type", "resource_id"}.issubset(columns):
        stmt = text(
            "DELETE FROM `sys_user_operate_log` WHERE `resource_type` = :resource_type AND `resource_id` IN :resource_ids"
        ).bindparams(bindparam("resource_ids", expanding=True))
        db.execute(stmt, {"resource_type": resource_type, "resource_ids": ids})


def _get_agency_and_descendant_ids(db: Session, root_agency_id: int) -> list[int]:
    result: list[int] = []
    visited: set[int] = set()
    queue: list[int] = [root_agency_id]
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        result.append(current_id)
        children = db.query(AgencyORM.id).filter(AgencyORM.parent_agency_id == current_id).all()
        queue.extend([row[0] for row in children])
    return result


def _to_domain(orm: AgencyORM) -> Agency:
    return Agency(
        id=orm.id,
        agency_code=orm.agency_code,
        agency_name=orm.agency_name,
        agency_type=orm.agency_type,
        agency_level=orm.agency_level,
        parent_agency_id=orm.parent_agency_id,
        region_code=orm.region_code,
        region_name=orm.region_name,
        contact_person=orm.contact_person,
        contact_phone=orm.contact_phone,
        status=orm.status,
        description=orm.description,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _to_orm(agency: Agency) -> AgencyORM:
    orm = AgencyORM(
        agency_code=agency.agency_code,
        agency_name=agency.agency_name,
        agency_type=agency.agency_type,
        agency_level=agency.agency_level,
        parent_agency_id=agency.parent_agency_id,
        region_code=agency.region_code,
        region_name=agency.region_name,
        contact_person=agency.contact_person,
        contact_phone=agency.contact_phone,
        status=agency.status,
        description=agency.description,
    )
    if agency.id is not None:
        orm.id = agency.id
    if agency.created_at is not None:
        orm.created_at = agency.created_at
    if agency.updated_at is not None:
        orm.updated_at = agency.updated_at
    return orm


class SQLAlchemyAgencyRepository(AgencyRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, agency_id: int) -> Agency | None:
        orm = self._db.query(AgencyORM).filter(AgencyORM.id == agency_id).first()
        return _to_domain(orm) if orm else None

    def get_by_code(self, agency_code: str) -> Agency | None:
        orm = self._db.query(AgencyORM).filter(AgencyORM.agency_code == agency_code).first()
        return _to_domain(orm) if orm else None

    def list_agencies(self, manageable_ids=None, keyword=None, agency_level=None, agency_type=None, status=None, parent_agency_id=None, page=1, page_size=10) -> tuple[list[Agency], int]:
        query = self._db.query(AgencyORM)
        if manageable_ids is not None:
            query = query.filter(AgencyORM.id.in_(manageable_ids))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(AgencyORM.agency_code.like(like), AgencyORM.agency_name.like(like)))
        if agency_level:
            query = query.filter(AgencyORM.agency_level == agency_level)
        if agency_type:
            query = query.filter(AgencyORM.agency_type == agency_type)
        if status:
            query = query.filter(AgencyORM.status == status)
        if parent_agency_id is not None:
            query = query.filter(AgencyORM.parent_agency_id == parent_agency_id)
        total = query.count()
        items = query.order_by(AgencyORM.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_to_domain(i) for i in items], total

    def get_agency_tree(self, manageable_ids=None) -> list[dict]:
        query = self._db.query(AgencyORM)
        if manageable_ids is not None:
            query = query.filter(AgencyORM.id.in_(manageable_ids))
        agencies = query.order_by(AgencyORM.id.asc()).all()
        item_map = {
            a.id: {"id": a.id, "label": a.agency_name, "agency_code": a.agency_code, "agency_name": a.agency_name,
                   "agency_level": a.agency_level, "agency_type": a.agency_type, "parent_agency_id": a.parent_agency_id,
                   "status": a.status, "children": []}
            for a in agencies
        }
        roots = []
        for a in agencies:
            item = item_map[a.id]
            if a.parent_agency_id and a.parent_agency_id in item_map:
                item_map[a.parent_agency_id]["children"].append(item)
            else:
                roots.append(item)
        return roots

    def save(self, agency: Agency) -> Agency:
        orm = _to_orm(agency)
        if agency.id is not None:
            existing = self._db.query(AgencyORM).filter(AgencyORM.id == agency.id).first()
            if existing:
                for col in ["agency_name", "agency_type", "agency_level", "parent_agency_id",
                            "region_code", "region_name", "contact_person", "contact_phone",
                            "description", "status"]:
                    setattr(existing, col, getattr(orm, col))
                existing.updated_at = agency.updated_at or datetime.now()
                self._db.flush()
                self._db.refresh(existing)
                return _to_domain(existing)
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _to_domain(orm)

    def delete(self, agency_id: int) -> dict:
        agency_ids = _get_agency_and_descendant_ids(self._db, agency_id)
        user_ids = _normalize_ids(self._db.query(SysUser.id).filter(SysUser.agency_id.in_(agency_ids)).all())
        node_ids = _normalize_ids(self._db.query(Node.id).filter(Node.agency_id.in_(agency_ids)).all())
        group_ids = sorted(set(
            _select_values_by_values(self._db, "group_member", "group_id", "agency_id", agency_ids)
            + _select_values_by_values(self._db, "group_info", "id", "agency_id", agency_ids)
            + _select_values_by_values(self._db, "group_info", "id", "owner_agency_id", agency_ids)
            + _select_values_by_values(self._db, "group_info", "id", "creator_agency_id", agency_ids)
        ))
        try:
            _delete_chain_records(self._db, "agency", agency_ids)
            _delete_chain_records(self._db, "user", user_ids)
            _delete_chain_records(self._db, "node", node_ids)
            _delete_operate_logs(self._db, "agency", agency_ids)
            _delete_operate_logs(self._db, "user", user_ids)
            _delete_operate_logs(self._db, "node", node_ids)
            _delete_by_values(self._db, "chain_record", "agency_id", agency_ids)
            _delete_by_values(self._db, "sys_user_operate_log", "agency_id", agency_ids)
            _delete_by_values(self._db, "sys_user_role_binding", "user_id", user_ids)
            _delete_by_values(self._db, "sys_user_group", "user_id", user_ids)
            _delete_by_values(self._db, "sys_user_group", "agency_id", agency_ids)
            _delete_by_values(self._db, "group_node", "node_id", node_ids)
            _delete_by_values(self._db, "group_node", "agency_id", agency_ids)
            _delete_by_values(self._db, "group_node", "group_id", group_ids)
            _delete_by_values(self._db, "group_member", "agency_id", agency_ids)
            _delete_by_values(self._db, "group_lifecycle_log", "agency_id", agency_ids)
            _delete_by_values(self._db, "group_lifecycle_log", "group_id", group_ids)
            _delete_fk_dependents(self._db, "agency", "id", agency_ids, skip_tables={"agency"})
            self._db.query(Node).filter(Node.id.in_(node_ids)).delete(synchronize_session=False)
            self._db.query(SysUser).filter(SysUser.id.in_(user_ids)).delete(synchronize_session=False)
            for delete_id in reversed(agency_ids):
                target = self._db.query(AgencyORM).filter(AgencyORM.id == delete_id).first()
                if target:
                    self._db.delete(target)
            self._db.commit()
            return {
                "deleted": True,
                "agency_id": agency_id,
                "deleted_agency_ids": agency_ids,
                "deleted_user_count": len(user_ids),
                "deleted_node_count": len(node_ids),
            }
        except Exception:
            self._db.rollback()
            raise

    def get_agency_and_descendant_ids(self, root_agency_id: int) -> list[int]:
        return _get_agency_and_descendant_ids(self._db, root_agency_id)

    def get_agency_name(self, agency_id: int | None) -> str | None:
        if not agency_id:
            return None
        agency = self._db.query(AgencyORM).filter(AgencyORM.id == agency_id).first()
        return agency.agency_name if agency else None

    def get_summary(self, agency_id: int) -> dict:
        child_count = self._db.query(AgencyORM).filter(AgencyORM.parent_agency_id == agency_id).count()
        user_count = 0
        try:
            user_count = self._db.query(SysUser).filter(SysUser.agency_id == agency_id).count()
        except Exception:
            pass
        node_count = self._db.query(Node).filter(Node.agency_id == agency_id).count()
        return {"child_count": child_count, "user_count": user_count, "node_count": node_count}
