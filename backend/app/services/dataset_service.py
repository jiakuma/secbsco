from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.models.dataset import Dataset
from app.schemas.dataset_schema import DatasetCreate, DatasetUpdate


class DatasetService:

    @staticmethod
    def list_datasets(
        db: Session,
        keyword: Optional[str] = None,
        agency_id: Optional[int] = None,
        dataset_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(Dataset)

        if keyword:
            query = query.filter(
                or_(
                    Dataset.dataset_code.like(f"%{keyword}%"),
                    Dataset.dataset_name.like(f"%{keyword}%")
                )
            )

        if agency_id:
            query = query.filter(Dataset.agency_id == agency_id)

        if dataset_type:
            query = query.filter(Dataset.dataset_type == dataset_type)

        if status:
            query = query.filter(Dataset.status == status)

        total = query.count()

        items = (
            query
            .order_by(Dataset.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_dataset_by_id(db: Session, dataset_id: int) -> Optional[Dataset]:
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()

    @staticmethod
    def get_dataset_by_code(db: Session, dataset_code: str) -> Optional[Dataset]:
        return db.query(Dataset).filter(Dataset.dataset_code == dataset_code).first()

    @staticmethod
    def get_agency_by_id(db: Session, agency_id: int) -> Optional[Agency]:
        return db.query(Agency).filter(Agency.id == agency_id).first()

    @staticmethod
    def create_dataset(db: Session, dataset_req: DatasetCreate) -> Dataset:
        dataset = Dataset(
            agency_id=dataset_req.agency_id,
            dataset_code=dataset_req.dataset_code,
            dataset_name=dataset_req.dataset_name,
            dataset_type=dataset_req.dataset_type,
            storage_uri=dataset_req.storage_uri,
            schema_json=dataset_req.schema_json,
            status=dataset_req.status or "enabled",
            description=dataset_req.description,
        )

        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        return dataset

    @staticmethod
    def update_dataset(
        db: Session,
        dataset: Dataset,
        dataset_req: DatasetUpdate
    ) -> Dataset:
        update_data = dataset_req.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(dataset, key, value)

        db.commit()
        db.refresh(dataset)

        return dataset

    @staticmethod
    def update_dataset_status(
        db: Session,
        dataset: Dataset,
        status: str
    ) -> Dataset:
        dataset.status = status

        db.commit()
        db.refresh(dataset)

        return dataset

    @staticmethod
    def build_dataset_info(dataset: Dataset) -> dict:
        return {
            "id": dataset.id,
            "agency_id": dataset.agency_id,
            "dataset_code": dataset.dataset_code,
            "dataset_name": dataset.dataset_name,
            "dataset_type": dataset.dataset_type,
            "storage_uri": dataset.storage_uri,
            "schema_json": dataset.schema_json,
            "status": dataset.status,
            "description": dataset.description,
            "created_at": dataset.created_at,
            "updated_at": dataset.updated_at,
        }