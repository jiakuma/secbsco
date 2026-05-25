from fastapi import HTTPException


class DatasetNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="数据集不存在")


class DatasetCodeAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="数据集编码已存在")


class DatasetAccessDenied(HTTPException):
    def __init__(self, detail: str = "无权访问该数据集"):
        super().__init__(status_code=403, detail=detail)


class AdminRequired(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="需要管理员权限")
