from typing import Optional

from pydantic import BaseModel


class NodeCreate(BaseModel):
    agency_id: int
    node_code: str
    node_name: str
    node_type: Optional[str] = None
    endpoint: Optional[str] = None
    status: Optional[str] = "offline"
    description: Optional[str] = None


class NodeUpdate(BaseModel):
    agency_id: Optional[int] = None
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    endpoint: Optional[str] = None
    description: Optional[str] = None


class NodeStatusUpdate(BaseModel):
    status: str