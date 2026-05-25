from fastapi import HTTPException


class AgencyNotFound(HTTPException):
    def __init__(self, detail: str = "机构不存在"):
        super().__init__(status_code=404, detail=detail)


class AgencyCodeDuplicate(HTTPException):
    def __init__(self, detail: str = "机构编码已存在"):
        super().__init__(status_code=400, detail=detail)


class InvalidAgencyStatus(HTTPException):
    def __init__(self, detail: str = "机构状态只能是 active 或 disabled"):
        super().__init__(status_code=400, detail=detail)


class ParentAgencyNotFound(HTTPException):
    def __init__(self, detail: str = "上级机构不存在"):
        super().__init__(status_code=404, detail=detail)


class SelfParentForbidden(HTTPException):
    def __init__(self, detail: str = "上级机构不能是自身"):
        super().__init__(status_code=400, detail=detail)


class DescendantParentForbidden(HTTPException):
    def __init__(self, detail: str = "上级机构不能选择自身或下级机构"):
        super().__init__(status_code=400, detail=detail)


class NoFieldsToUpdate(HTTPException):
    def __init__(self, detail: str = "没有需要更新的字段"):
        super().__init__(status_code=400, detail=detail)
