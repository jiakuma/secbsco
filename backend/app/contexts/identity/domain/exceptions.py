from fastapi import HTTPException


class UserNotFound(HTTPException):
    def __init__(self, detail: str = "用户不存在"):
        super().__init__(status_code=404, detail=detail)


class UserAlreadyExists(HTTPException):
    def __init__(self, detail: str = "用户名已存在"):
        super().__init__(status_code=400, detail=detail)


class InvalidCredentials(HTTPException):
    def __init__(self, detail: str = "用户名或密码错误，或用户已被禁用"):
        super().__init__(status_code=401, detail=detail)


class UserDisabled(HTTPException):
    def __init__(self, detail: str = "用户已禁用"):
        super().__init__(status_code=400, detail=detail)


class PermissionDenied(HTTPException):
    def __init__(self, detail: str = "权限不足"):
        super().__init__(status_code=403, detail=detail)


class GroupNotFound(HTTPException):
    def __init__(self, detail: str = "资源不存在或无权访问"):
        super().__init__(status_code=404, detail=detail)
