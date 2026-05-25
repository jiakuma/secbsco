from fastapi import HTTPException


class NodeNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="节点不存在")


class NodeCodeAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="节点编码已存在")


class NodeAgencyNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="所属机构不存在")


class InvalidNodeType(HTTPException):
    def __init__(self, node_type: str):
        super().__init__(status_code=400, detail=f"节点类型不合法: {node_type}")


class InvalidNodeStatus(HTTPException):
    def __init__(self, status: str):
        super().__init__(status_code=400, detail=f"节点状态不合法: {status}")


class InvalidNodeCapability(HTTPException):
    def __init__(self, cap: str):
        super().__init__(status_code=400, detail=f"节点能力不合法：{cap}")


class NoFieldsToUpdate(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="没有需要更新的字段")


class AgentNotConfigured(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="节点未配置Agent地址")
