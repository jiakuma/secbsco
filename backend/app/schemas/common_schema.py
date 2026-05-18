"""通用 Schema：分页、列表响应等。"""

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


class IdRequest(BaseModel):
    id: int
