from fastapi import HTTPException


class TemplateNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="模板不存在")


class TemplateCodeAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="模板编码已存在")


class TemplateAccessDenied(HTTPException):
    def __init__(self, detail: str = "无权访问该模板"):
        super().__init__(status_code=403, detail=detail)


class TemplateProtected(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="该模板为系统核心模板，不允许删除")


class AdminRequired(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="需要管理员权限")
