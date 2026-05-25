from datetime import datetime
from .enums import AgencyStatus


class Agency:
    def __init__(
        self,
        id: int | None = None,
        agency_code: str = "",
        agency_name: str = "",
        agency_type: str | None = None,
        agency_level: str | None = None,
        parent_agency_id: int | None = None,
        region_code: str | None = None,
        region_name: str | None = None,
        contact_person: str | None = None,
        contact_phone: str | None = None,
        status: str = "active",
        description: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.agency_code = agency_code
        self.agency_name = agency_name
        self.agency_type = agency_type
        self.agency_level = agency_level
        self.parent_agency_id = parent_agency_id
        self.region_code = region_code
        self.region_name = region_name
        self.contact_person = contact_person
        self.contact_phone = contact_phone
        self._status = status
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def status(self) -> str:
        return self._status

    def is_active(self) -> bool:
        return self._status == AgencyStatus.ACTIVE.value

    def enable(self) -> None:
        self._status = AgencyStatus.ACTIVE.value

    def disable(self) -> None:
        self._status = AgencyStatus.DISABLED.value

    def set_status(self, status: str) -> None:
        if status not in (AgencyStatus.ACTIVE.value, AgencyStatus.DISABLED.value):
            from .exceptions import InvalidAgencyStatus
            raise InvalidAgencyStatus()
        self._status = status

    def update_fields(self, **fields) -> None:
        updatable = [
            "agency_name", "agency_type", "agency_level", "parent_agency_id",
            "region_code", "region_name", "contact_person", "contact_phone", "description",
        ]
        changed = False
        for f in updatable:
            if f in fields and fields[f] is not None:
                setattr(self, f, fields[f])
                changed = True
        if not changed:
            from .exceptions import NoFieldsToUpdate
            raise NoFieldsToUpdate()
        self.updated_at = datetime.now()
