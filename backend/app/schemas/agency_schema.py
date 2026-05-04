from typing import Optional

from pydantic import BaseModel


class AgencyCreate(BaseModel):
    agency_code: str
    agency_name: str
    agency_type: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = "enabled"
    description: Optional[str] = None


class AgencyUpdate(BaseModel):
    agency_name: Optional[str] = None
    agency_type: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    description: Optional[str] = None


class AgencyStatusUpdate(BaseModel):
    status: str