from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.agency import Agency
from app.schemas.agency_schema import AgencyCreate, AgencyUpdate


class AgencyService:

    @staticmethod
    def list_agencies(
        db: Session,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(Agency)

        if keyword:
            query = query.filter(
                or_(
                    Agency.agency_code.like(f"%{keyword}%"),
                    Agency.agency_name.like(f"%{keyword}%")
                )
            )

        if status:
            query = query.filter(Agency.status == status)

        total = query.count()

        items = (
            query
            .order_by(Agency.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_agency_by_id(db: Session, agency_id: int) -> Optional[Agency]:
        return db.query(Agency).filter(Agency.id == agency_id).first()

    @staticmethod
    def get_agency_by_code(db: Session, agency_code: str) -> Optional[Agency]:
        return db.query(Agency).filter(Agency.agency_code == agency_code).first()

    @staticmethod
    def create_agency(db: Session, agency_req: AgencyCreate) -> Agency:
        agency = Agency(
            agency_code=agency_req.agency_code,
            agency_name=agency_req.agency_name,
            agency_type=agency_req.agency_type,
            contact_person=agency_req.contact_person,
            contact_phone=agency_req.contact_phone,
            status=agency_req.status or "enabled",
            description=agency_req.description,
        )

        db.add(agency)
        db.commit()
        db.refresh(agency)

        return agency

    @staticmethod
    def update_agency(
        db: Session,
        agency: Agency,
        agency_req: AgencyUpdate
    ) -> Agency:
        update_data = agency_req.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(agency, key, value)

        db.commit()
        db.refresh(agency)

        return agency

    @staticmethod
    def update_agency_status(
        db: Session,
        agency: Agency,
        status: str
    ) -> Agency:
        agency.status = status

        db.commit()
        db.refresh(agency)

        return agency

    @staticmethod
    def build_agency_info(agency: Agency) -> dict:
        return {
            "id": agency.id,
            "agency_code": agency.agency_code,
            "agency_name": agency.agency_name,
            "agency_type": agency.agency_type,
            "contact_person": agency.contact_person,
            "contact_phone": agency.contact_phone,
            "status": agency.status,
            "description": agency.description,
            "created_at": agency.created_at,
            "updated_at": agency.updated_at,
        }