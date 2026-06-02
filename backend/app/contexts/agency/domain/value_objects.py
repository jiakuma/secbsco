# domain/value_objects.py

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UserContext:
    """表示当前操作的用户上下文（领域层安全对象）"""
    id: int
    username: str
    real_name: Optional[str]
    agency_id: Optional[int]


@dataclass(frozen=True)
class AuditMetadata:
    """审计元数据（不含 db session 和 request）"""
    operation_type: str
    resource_type: str
    resource_id: int
    agency_id: Optional[int] = None


@dataclass(frozen=True)
class ContactInfo:
    """机构联系人信息"""
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


@dataclass(frozen=True)
class Region:
    """机构区域信息"""
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None