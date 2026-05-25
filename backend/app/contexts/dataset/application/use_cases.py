from ..domain.models import DatasetInfo
from ..domain.ports import DatasetRepository, AccessControlPort, AgencyQueryPort, NodeQueryPort
from ..domain.exceptions import DatasetNotFound, DatasetCodeAlreadyExists
from .dtos import DatasetDTO, PaginatedDatasetsDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_dto(ds: DatasetInfo, agency_name: str | None = None, node_name: str | None = None) -> DatasetDTO:
    return DatasetDTO(
        id=ds.id, dataset_code=ds.dataset_code, dataset_name=ds.dataset_name,
        agency_id=ds.agency_id, agency_name=agency_name,
        node_id=ds.node_id, node_name=node_name,
        data_type=ds.data_type, data_location=ds.data_location,
        storage_uri=ds.storage_uri, dataset_type=ds.dataset_type,
        description=ds.description, status=ds.status,
        created_at=_format_dt(ds.created_at), updated_at=_format_dt(ds.updated_at),
    )


class ListDatasetsUseCase:
    def __init__(self, repo: DatasetRepository, access_control: AccessControlPort, agency: AgencyQueryPort, node: NodeQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency
        self._node = node

    def execute(self, current_user, **filters) -> PaginatedDatasetsDTO:
        visible_ids = self._access_control.get_visible_agency_ids(current_user)
        agency_id = filters.get("agency_id")
        if agency_id and visible_ids is not None and agency_id not in visible_ids:
            return PaginatedDatasetsDTO(total=0, page=filters.get("page", 1), page_size=filters.get("page_size", 10))
        datasets, total = self._repo.list_datasets(visible_agency_ids=visible_ids, **filters)
        items = [_to_dto(d, self._agency.get_agency_name(d.agency_id), self._node.get_node_name(d.node_id)) for d in datasets]
        return PaginatedDatasetsDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetDatasetDetailUseCase:
    def __init__(self, repo: DatasetRepository, access_control: AccessControlPort, agency: AgencyQueryPort, node: NodeQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency
        self._node = node

    def execute(self, dataset_id: int, current_user) -> DatasetDTO:
        ds = self._repo.get_by_id(dataset_id)
        if not ds:
            raise DatasetNotFound()
        self._access_control.check_dataset_access(current_user, ds)
        return _to_dto(ds, self._agency.get_agency_name(ds.agency_id), self._node.get_node_name(ds.node_id))


class CreateDatasetUseCase:
    def __init__(self, repo: DatasetRepository, access_control: AccessControlPort, agency: AgencyQueryPort, node: NodeQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency
        self._node = node

    def execute(self, payload: dict, current_user) -> DatasetDTO:
        self._access_control.require_admin(current_user)
        visible_ids = self._access_control.get_visible_agency_ids(current_user)
        agency_id = payload.get("agency_id")
        if visible_ids is not None and agency_id not in visible_ids:
            from ..domain.exceptions import DatasetAccessDenied
            raise DatasetAccessDenied("无权在该机构下创建数据集")
        if self._repo.get_by_code(payload.get("dataset_code")):
            raise DatasetCodeAlreadyExists()
        ds = DatasetInfo(
            agency_id=agency_id, node_id=payload.get("node_id"),
            dataset_code=payload.get("dataset_code"), dataset_name=payload.get("dataset_name"),
            data_type=payload.get("data_type"), data_location=payload.get("data_location"),
            storage_uri=payload.get("storage_uri") or payload.get("data_location"),
            dataset_type=payload.get("dataset_type"), schema_json=payload.get("schema_json"),
            status=payload.get("status", "enabled"), created_by=current_user.id,
            description=payload.get("description"),
        )
        ds = self._repo.save(ds)
        return _to_dto(ds, self._agency.get_agency_name(ds.agency_id), self._node.get_node_name(ds.node_id))


class UpdateDatasetUseCase:
    def __init__(self, repo: DatasetRepository, access_control: AccessControlPort, agency: AgencyQueryPort, node: NodeQueryPort):
        self._repo = repo
        self._access_control = access_control
        self._agency = agency
        self._node = node

    def execute(self, dataset_id: int, payload: dict, current_user) -> DatasetDTO:
        ds = self._repo.get_by_id(dataset_id)
        if not ds:
            raise DatasetNotFound()
        self._access_control.check_dataset_access(current_user, ds, require_write=True)
        update_fields = ["agency_id", "dataset_name", "node_id", "data_type", "data_location", "dataset_type", "storage_uri", "schema_json", "description"]
        for f in update_fields:
            if f in payload:
                setattr(ds, f, payload[f])
        ds = self._repo.save(ds)
        return _to_dto(ds, self._agency.get_agency_name(ds.agency_id), self._node.get_node_name(ds.node_id))


class DeleteDatasetUseCase:
    def __init__(self, repo: DatasetRepository, access_control: AccessControlPort):
        self._repo = repo
        self._access_control = access_control

    def execute(self, dataset_id: int, current_user) -> dict:
        ds = self._repo.get_by_id(dataset_id)
        if not ds:
            raise DatasetNotFound()
        self._access_control.check_dataset_access(current_user, ds, require_write=True)
        self._repo.delete(dataset_id)
        return {"id": dataset_id}
