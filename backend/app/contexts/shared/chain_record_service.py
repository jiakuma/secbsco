import hashlib
import json
import time
from datetime import date, datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.models.chain_record import ChainRecord
from app.schemas.chain_record_schema import ChainRecordCreate


def _to_jsonable(value: Any):
    """
    将 datetime / date 等对象转为 JSON 可序列化格式。
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _to_jsonable(item)
            for item in value
        ]

    return value


class ChainRecordService:

    @staticmethod
    def list_records(
        db: Session,
        biz_type: Optional[str] = None,
        biz_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(ChainRecord)

        if biz_type:
            query = query.filter(ChainRecord.biz_type == biz_type)

        if biz_id:
            query = query.filter(ChainRecord.biz_id == biz_id)

        if status:
            query = query.filter(ChainRecord.status == status)

        total = query.count()

        items = (
            query
            .order_by(ChainRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_record_by_id(
        db: Session,
        record_id: int
    ) -> Optional[ChainRecord]:
        return (
            db.query(ChainRecord)
            .filter(ChainRecord.id == record_id)
            .first()
        )

    @staticmethod
    def get_record_by_biz(
        db: Session,
        biz_type: str,
        biz_id: str,
        content_hash: str
    ) -> Optional[ChainRecord]:
        return (
            db.query(ChainRecord)
            .filter(
                ChainRecord.biz_type == biz_type,
                ChainRecord.biz_id == biz_id,
                ChainRecord.content_hash == content_hash,
            )
            .first()
        )

    @staticmethod
    def generate_content_hash(content: dict) -> str:
        content_text = json.dumps(
            _to_jsonable(content),
            ensure_ascii=False,
            sort_keys=True
        )
        return hashlib.sha256(content_text.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_mock_tx_hash(
        biz_type: str,
        biz_id: str,
        content_hash: str
    ) -> str:
        raw = f"{biz_type}:{biz_id}:{content_hash}:{time.time()}"
        return "0x" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def create_record(
        db: Session,
        record_req: ChainRecordCreate
    ) -> ChainRecord:
        record = ChainRecord(
            biz_type=record_req.biz_type,
            biz_id=record_req.biz_id,
            content_hash=record_req.content_hash,
            chain_type=record_req.chain_type or "fisco_bcos",
            tx_hash=record_req.tx_hash,
            block_number=record_req.block_number,
            contract_address=record_req.contract_address,
            status=record_req.status or "success",
            error_message=record_req.error_message,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    @staticmethod
    def mock_anchor_content(
        db: Session,
        biz_type: str,
        biz_id: str,
        content: dict
    ) -> ChainRecord:
        """
        Mock 链上存证：
        1. 对业务内容生成 SHA256 内容哈希
        2. 生成模拟 tx_hash
        3. 生成模拟 block_number
        4. 写入 chain_record
        """
        content_hash = ChainRecordService.generate_content_hash(content)

        existed = ChainRecordService.get_record_by_biz(
            db=db,
            biz_type=biz_type,
            biz_id=biz_id,
            content_hash=content_hash
        )

        if existed:
            return existed

        tx_hash = ChainRecordService.generate_mock_tx_hash(
            biz_type=biz_type,
            biz_id=biz_id,
            content_hash=content_hash
        )

        block_number = int(time.time())

        record_req = ChainRecordCreate(
            biz_type=biz_type,
            biz_id=biz_id,
            content_hash=content_hash,
            chain_type="fisco_bcos",
            tx_hash=tx_hash,
            block_number=block_number,
            contract_address="mock_contract_address",
            status="success",
            error_message=None,
        )

        return ChainRecordService.create_record(
            db=db,
            record_req=record_req
        )

    @staticmethod
    def build_record_info(record: ChainRecord) -> dict:
        return {
            "id": record.id,
            "biz_type": record.biz_type,
            "biz_id": record.biz_id,
            "content_hash": record.content_hash,
            "chain_type": record.chain_type,
            "tx_hash": record.tx_hash,
            "block_number": record.block_number,
            "contract_address": record.contract_address,
            "status": record.status,
            "error_message": record.error_message,
            "created_at": record.created_at,
        }