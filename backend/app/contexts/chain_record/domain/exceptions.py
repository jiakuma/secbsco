from fastapi import HTTPException


class ChainRecordNotFoundError(Exception):
    pass


def raise_chain_record_not_found(record_id: int):
    raise HTTPException(status_code=404, detail="存证记录不存在")
