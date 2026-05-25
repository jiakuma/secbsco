from fastapi import HTTPException


class GroupNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="群组不存在")


class GroupNotEditable(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="当前状态不允许编辑")


class GroupNotPendingApproval(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="群组不在待审批状态")


class GroupNotDissolving(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="群组不在删除审批状态")


class CannotRemoveLeadAgency(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="不能移除牵头机构")


class MemberHasNodes(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="该机构下有节点授权到群组，请先撤销节点授权")


class GroupHasRunningTasks(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="群组下有正在运行的任务，请先停止任务")


class CannotApproveGroup(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="无权审批该群组")


class AdminRequired(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail="需要管理员权限")


class GroupAccessDenied(HTTPException):
    def __init__(self, detail: str = "无权访问该群组"):
        super().__init__(status_code=403, detail=detail)


class MemberAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="机构已是群组成员")


class AgencyNotInGroup(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="机构不是群组成员")
