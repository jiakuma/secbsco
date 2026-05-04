from typing import Optional

from pydantic import BaseModel


class ChainRecordCreate(BaseModel):
    biz_type: str
    biz_id: str
    content_hash: str

    chain_type: Optional[str] = "fisco_bcos"
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    contract_address: Optional[str] = None

    status: Optional[str] = "success"
    error_message: Optional[str] = None