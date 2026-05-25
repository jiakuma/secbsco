from fastapi import HTTPException


class TaskNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="任务不存在")


class TaskCodeAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="任务编码已存在")


class TaskAccessDenied(HTTPException):
    def __init__(self, detail: str = "无权访问该任务"):
        super().__init__(status_code=403, detail=detail)


class TaskResultNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="任务结果不存在")
