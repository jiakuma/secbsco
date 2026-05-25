from enum import Enum


class AgencyType(str, Enum):
    CDC = "cdc"
    HOSPITAL = "hospital"
    LAB = "lab"
    HEALTH_COMMISSION = "health_commission"
    RESEARCH = "research"
    OTHER = "other"


class AgencyLevel(str, Enum):
    COUNTY = "county"
    CITY = "city"
    PROVINCE = "province"
    NATIONAL = "national"


class AgencyStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
