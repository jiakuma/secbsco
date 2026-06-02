from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.dataset import Dataset as DatasetORM
from app.models.agency import Agency
from app.models.node import Node as NodeORM
from ..domain.models import DatasetInfo
from ..domain.ports import DatasetRepository, AccessControlPort, AgencyQueryPort, NodeQueryPort


def _to_domain(orm: DatasetORM) -> DatasetInfo:
    return DatasetInfo(
        id=orm.id, agency_id=orm.agency_id, node_id=orm.node_id,
        dataset_code=orm.dataset_code, dataset_name=orm.dataset_name,
        data_type=orm.data_type, data_location=orm.data_location,
        dataset_type=orm.dataset_type, storage_uri=orm.storage_uri,
        schema_json=orm.schema_json, template_id=orm.template_id,
        status=orm.status, version=orm.version, created_by=orm.created_by,
        description=orm.description, created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _apply_to_orm(orm: DatasetORM, ds: DatasetInfo) -> None:
    for attr in ["agency_id", "node_id", "dataset_code", "dataset_name", "data_type",
                 "data_location", "dataset_type", "storage_uri", "schema_json", "description"]:
        setattr(orm, attr, getattr(ds, attr))


class SQLAlchemyDatasetRepository(DatasetRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, dataset_id: int) -> DatasetInfo | None:
        orm = self._db.query(DatasetORM).filter(DatasetORM.id == dataset_id).first()
        return _to_domain(orm) if orm else None

    def get_by_code(self, dataset_code: str) -> DatasetInfo | None:
        orm = self._db.query(DatasetORM).filter(DatasetORM.dataset_code == dataset_code).first()
        return _to_domain(orm) if orm else None

    def list_datasets(self, *, visible_agency_ids=None, keyword=None, agency_id=None, page=1, page_size=10) -> tuple[list[DatasetInfo], int]:
        query = self._db.query(DatasetORM)
        if visible_agency_ids is not None:
            query = query.filter(DatasetORM.agency_id.in_(visible_agency_ids))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(DatasetORM.dataset_code.like(like), DatasetORM.dataset_name.like(like)))
        if agency_id:
            query = query.filter(DatasetORM.agency_id == agency_id)
        total = query.count()
        items = query.order_by(DatasetORM.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_to_domain(i) for i in items], total

    def save(self, dataset: DatasetInfo) -> DatasetInfo:
        if dataset.id is not None:
            orm = self._db.query(DatasetORM).filter(DatasetORM.id == dataset.id).first()
            if orm:
                _apply_to_orm(orm, dataset)
                self._db.flush()
                self._db.refresh(orm)
                return _to_domain(orm)
        orm = DatasetORM(
            agency_id=dataset.agency_id, node_id=dataset.node_id,
            dataset_code=dataset.dataset_code, dataset_name=dataset.dataset_name,
            data_type=dataset.data_type, data_location=dataset.data_location,
            dataset_type=dataset.dataset_type, storage_uri=dataset.storage_uri,
            schema_json=dataset.schema_json, status=dataset.status,
            created_by=dataset.created_by, description=dataset.description,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _to_domain(orm)

    def delete(self, dataset_id: int) -> None:
        ds = self._db.query(DatasetORM).filter(DatasetORM.id == dataset_id).first()
        if ds:
            self._db.delete(ds)
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

    def check_dataset_access(self, current_user, dataset, require_write: bool = False) -> None:
        from app.contexts.shared.access_control_service import is_platform_admin, is_agency_admin, is_ancestor_agency
        from fastapi import HTTPException
        if is_platform_admin(self._db, current_user.id):
            return
        if require_write and not is_agency_admin(self._db, current_user.id):
            raise HTTPException(status_code=403, detail="需要管理员权限")
        if current_user.agency_id == dataset.agency_id:
            return
        if is_agency_admin(self._db, current_user.id) and is_ancestor_agency(self._db, current_user.agency_id, dataset.agency_id):
            return
        raise HTTPException(status_code=403, detail="无权访问该数据集")

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


class BridgeNodeQueryPort(NodeQueryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_node_name(self, node_id: int | None) -> str | None:
        if not node_id:
            return None
        n = self._db.query(NodeORM).filter(NodeORM.id == node_id).first()
        return n.node_name if n else None
