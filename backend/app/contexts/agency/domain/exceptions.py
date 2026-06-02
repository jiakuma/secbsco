# domain/exceptions.py

class DomainError(Exception):
    """领域异常基类"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)


class AgencyNotFound(DomainError):
    def __init__(self):
        super().__init__("机构不存在", code="AGENCY_NOT_FOUND")


class AgencyCodeDuplicate(DomainError):
    def __init__(self):
        super().__init__("机构编码已存在", code="AGENCY_CODE_DUPLICATE")


class InvalidAgencyStatus(DomainError):
    def __init__(self):
        super().__init__("机构状态只能是 active 或 disabled", code="INVALID_AGENCY_STATUS")


class ParentAgencyNotFound(DomainError):
    def __init__(self):
        super().__init__("上级机构不存在", code="PARENT_AGENCY_NOT_FOUND")


class SelfParentForbidden(DomainError):
    def __init__(self):
        super().__init__("上级机构不能是自身", code="SELF_PARENT_FORBIDDEN")


class DescendantParentForbidden(DomainError):
    def __init__(self):
        super().__init__("上级机构不能选择自身或下级机构", code="DESCENDANT_PARENT_FORBIDDEN")


class NoFieldsToUpdate(DomainError):
    def __init__(self):
        super().__init__("没有需要更新的字段", code="NO_FIELDS_TO_UPDATE")