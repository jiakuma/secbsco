from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.stat_template import StatTemplate as TemplateORM
from app.models.agency import Agency
from ..domain.models import TemplateInfo
from ..domain.ports import TemplateRepository, AccessControlPort, AgencyQueryPort


def _to_domain(orm: TemplateORM) -> TemplateInfo:
    return TemplateInfo(
        id=orm.id, agency_id=orm.agency_id,
        template_code=orm.template_code, template_name=orm.template_name,
        scenario=orm.scenario, exec_mode=orm.exec_mode, output_type=orm.output_type,
        stat_type=orm.stat_type, metrics_json=orm.metrics_json,
        params_schema_json=orm.params_schema_json, executor_config_json=orm.executor_config_json,
        input_requirements_json=orm.input_requirements_json, output_view_type=orm.output_view_type,
        template_hash=orm.template_hash, status=orm.status, version=orm.version,
        created_by=orm.created_by, description=orm.description,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _apply_to_orm(orm: TemplateORM, t: TemplateInfo) -> None:
    for attr in ["agency_id", "template_code", "template_name", "scenario", "exec_mode",
                 "output_type", "stat_type", "metrics_json", "params_schema_json",
                 "executor_config_json", "input_requirements_json", "output_view_type", "description"]:
        setattr(orm, attr, getattr(t, attr))


class SQLAlchemyTemplateRepository(TemplateRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, template_id: int) -> TemplateInfo | None:
        orm = self._db.query(TemplateORM).filter(TemplateORM.id == template_id).first()
        return _to_domain(orm) if orm else None

    def get_by_code(self, template_code: str) -> TemplateInfo | None:
        orm = self._db.query(TemplateORM).filter(TemplateORM.template_code == template_code).first()
        return _to_domain(orm) if orm else None

    def list_templates(self, *, visible_agency_ids=None, keyword=None, agency_id=None, page=1, page_size=10) -> tuple[list[TemplateInfo], int]:
        query = self._db.query(TemplateORM)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(TemplateORM.template_code.like(like), TemplateORM.template_name.like(like)))
        if agency_id:
            query = query.filter(TemplateORM.agency_id == agency_id)
        if visible_agency_ids is not None:
            query = query.filter(
                (TemplateORM.agency_id.in_(visible_agency_ids)) | (TemplateORM.agency_id.is_(None))
            )
        total = query.count()
        items = query.order_by(TemplateORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_to_domain(i) for i in items], total

    def save(self, template: TemplateInfo) -> TemplateInfo:
        if template.id is not None:
            orm = self._db.query(TemplateORM).filter(TemplateORM.id == template.id).first()
            if orm:
                _apply_to_orm(orm, template)
                self._db.flush()
                self._db.refresh(orm)
                return _to_domain(orm)
        orm = TemplateORM(
            agency_id=template.agency_id,
            template_code=template.template_code, template_name=template.template_name,
            scenario=template.scenario, exec_mode=template.exec_mode,
            output_type=template.output_type, description=template.description,
            created_by=template.created_by,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _to_domain(orm)

    def delete(self, template_id: int) -> None:
        orm = self._db.query(TemplateORM).filter(TemplateORM.id == template_id).first()
        if not orm:
            return
        from app.models.group import GroupTaskTemplate
        from app.models.task import Task
        self._db.query(GroupTaskTemplate).filter(GroupTaskTemplate.template_id == template_id).delete()
        self._db.query(Task).filter(Task.template_id == template_id).update({Task.template_id: None})
        self._db.delete(orm)
        self._db.flush()


class BridgeAccessControlPort(AccessControlPort):
    def __init__(self, db: Session):
        self._db = db

    def get_visible_agency_ids(self, current_user) -> list[int] | None:
        from app.contexts.shared.access_control_service import is_platform_admin, is_agency_admin
        if is_platform_admin(self._db, current_user.id):
            return None
        user_agency_id = current_user.agency_id
        if not user_agency_id:
            return []
        agency_ids = [user_agency_id]
        if is_agency_admin(self._db, current_user.id):
            def collect(parent_id: int):
                children = self._db.query(Agency.id).filter(
                    Agency.parent_agency_id == parent_id, Agency.status == "active",
                ).all()
                for child in children:
                    cid = child[0]
                    if cid not in agency_ids:
                        agency_ids.append(cid)
                        collect(cid)
            collect(user_agency_id)
        return agency_ids

    def check_template_access(self, current_user, template, require_write: bool = False) -> None:
        from app.contexts.shared.access_control_service import is_platform_admin, is_agency_admin, is_ancestor_agency
        from fastapi import HTTPException
        if is_platform_admin(self._db, current_user.id):
            return
        if require_write and not is_agency_admin(self._db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")
        if not template.agency_id:
            return
        if current_user.agency_id == template.agency_id:
            return
        if is_agency_admin(self._db, current_user.id) and is_ancestor_agency(self._db, current_user.agency_id, template.agency_id):
            return
        raise HTTPException(status_code=403, detail="无权访问该模板")

    def require_admin(self, current_user) -> None:
        from app.contexts.shared.access_control_service import is_platform_admin, is_agency_admin
        from fastapi import HTTPException
        if not is_platform_admin(self._db, current_user.id) and not is_agency_admin(self._db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")


class BridgeAgencyQueryPort(AgencyQueryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_agency_name(self, agency_id: int | None) -> str | None:
        if not agency_id:
            return None
        a = self._db.query(Agency).filter(Agency.id == agency_id).first()
        return a.agency_name if a else None
