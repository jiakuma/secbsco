# domain/__init__.py

from .enums import AgencyType, AgencyLevel, AgencyStatus
from .models import Agency
from .value_objects import ContactInfo, Region
from .ports import AgencyRepository, AgencyPermissionPort, AgencyAuditPort
from .exceptions import (
    DomainError,
    AgencyNotFound,
    AgencyCodeDuplicate,
    InvalidAgencyStatus,
    ParentAgencyNotFound,
    SelfParentForbidden,
    DescendantParentForbidden,
    NoFieldsToUpdate,
)