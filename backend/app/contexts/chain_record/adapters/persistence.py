import hashlib
import json
import time
from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.chain_record import ChainRecord as ChainRecordORM
from app.models.task_result import TaskResult as TaskResultORM
from app.models.audit_log import AuditLog as AuditLogORM
from app.models.task import Task as TaskORM
from ..domain.models import ChainRecordInfo, RelatedTaskInfo
from ..domain.ports import ChainRecordRepository, RelatedTaskPort, TaskLookupPort, AuditLogLookupPort, TaskResultLookupPort


def _to_domain(orm: ChainRecordORM) -> ChainRecordInfo:
    return ChainRecordInfo(
        id=orm.id,
        biz_type=orm.biz_type,
        biz_id=orm.biz_id,
        content_hash=orm.content_hash,
        chain_type=orm.chain_type,
        tx_hash=orm.tx_hash,
        block_number=orm.block_number,
        contract_address=orm.contract_address,
        status=orm.status,
        error_message=orm.error_message,
        created_at=orm.created_at,
        anchor_id=getattr(orm, "anchor_id", None),
        group_id=getattr(orm, "group_id", None),
        agency_id=getattr(orm, "agency_id", None),
        task_id=getattr(orm, "task_id", None),
        result_id=getattr(orm, "result_id", None),
        dataset_id=getattr(orm, "dataset_id", None),
        contract_name=getattr(orm, "contract_name", None),
        contract_version=getattr(orm, "contract_version", None),
        verify_status=getattr(orm, "verify_status", None),
        last_verify_time=getattr(orm, "last_verify_time", None),
        verify_detail_json=getattr(orm, "verify_detail_json", None),
        updated_at=getattr(orm, "updated_at", None),
    )


def _to_jsonable(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    return value


def build_record_info(record: ChainRecordORM) -> dict:
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


def build_result_info(result: TaskResultORM) -> dict:
    return {
        "id": result.id,
        "task_id": result.task_id,
        "result_json": result.result_json,
        "metrics_json": result.metrics_json,
        "result_hash": result.result_hash,
        "status": result.status,
        "error_message": result.error_message,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


def build_log_info(log: AuditLogORM) -> dict:
    return {
        "id": log.id,
        "task_id": log.task_id,
        "agency_id": log.agency_id,
        "operator_user_id": log.operator_user_id,
        "operation_type": log.operation_type,
        "object_type": log.object_type,
        "object_id": log.object_id,
        "operation_desc": log.operation_desc,
        "request_json": log.request_json,
        "result_json": log.result_json,
        "ip_address": log.ip_address,
        "created_at": log.created_at,
    }


def generate_content_hash(content: dict) -> str:
    content_text = json.dumps(_to_jsonable(content), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()


def generate_mock_tx_hash(biz_type: str, biz_id: str, content_hash: str) -> str:
    raw = f"{biz_type}:{biz_id}:{content_hash}:{time.time()}"
    return "0x" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SQLAlchemyChainRecordRepository(ChainRecordRepository):
    def __init__(self, db: Session):
        self._db = db

    def list_records(
        self,
        biz_type: Optional[str] = None,
        biz_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[ChainRecordInfo]]:
        query = self._db.query(ChainRecordORM)
        if biz_type:
            query = query.filter(ChainRecordORM.biz_type == biz_type)
        if biz_id:
            query = query.filter(ChainRecordORM.biz_id == biz_id)
        if status:
            query = query.filter(ChainRecordORM.status == status)
        total = query.count()
        items = (
            query
            .order_by(ChainRecordORM.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, [_to_domain(i) for i in items]

    def get_by_id(self, record_id: int) -> Optional[ChainRecordInfo]:
        orm = self._db.query(ChainRecordORM).filter(ChainRecordORM.id == record_id).first()
        if not orm:
            return None
        return _to_domain(orm)

    def get_record_by_biz(self, biz_type: str, biz_id: str, content_hash: str) -> Optional[ChainRecordORM]:
        return (
            self._db.query(ChainRecordORM)
            .filter(
                ChainRecordORM.biz_type == biz_type,
                ChainRecordORM.biz_id == biz_id,
                ChainRecordORM.content_hash == content_hash,
            )
            .first()
        )

    def create_record(self, biz_type: str, biz_id: str, content_hash: str,
                      chain_type: str = "fisco_bcos", tx_hash: str | None = None,
                      block_number: int | None = None, contract_address: str | None = None,
                      status: str = "success", error_message: str | None = None) -> ChainRecordORM:
        record = ChainRecordORM(
            biz_type=biz_type, biz_id=biz_id, content_hash=content_hash,
            chain_type=chain_type or "fisco_bcos", tx_hash=tx_hash,
            block_number=block_number, contract_address=contract_address,
            status=status or "success", error_message=error_message,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def mock_anchor_content(self, biz_type: str, biz_id: str, content: dict) -> ChainRecordORM:
        content_hash = generate_content_hash(content)
        existed = self.get_record_by_biz(biz_type=biz_type, biz_id=biz_id, content_hash=content_hash)
        if existed:
            return existed
        tx_hash = generate_mock_tx_hash(biz_type=biz_type, biz_id=biz_id, content_hash=content_hash)
        block_number = int(time.time())
        return self.create_record(
            biz_type=biz_type, biz_id=biz_id, content_hash=content_hash,
            chain_type="fisco_bcos", tx_hash=tx_hash,
            block_number=block_number, contract_address="mock_contract_address",
            status="success", error_message=None,
        )


def _safe_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


class BridgeRelatedTaskPort(RelatedTaskPort):
    def __init__(self, db: Session):
        self._db = db

    def build_related_task(self, biz_type: str, biz_id: str) -> Optional[RelatedTaskInfo]:
        biz_id_int = _safe_int(biz_id)
        if not biz_type or biz_id_int is None:
            return None
        task_id: int | None = None
        if biz_type == "task":
            task_id = biz_id_int
        elif biz_type == "task_result":
            result = self._db.query(TaskResultORM).filter(TaskResultORM.id == biz_id_int).first()
            task_id = result.task_id if result else None
        elif biz_type == "audit_log":
            log = self._db.query(AuditLogORM).filter(AuditLogORM.id == biz_id_int).first()
            task_id = log.task_id if log else None
        if not task_id:
            return None
        task = self._db.query(TaskORM).filter(TaskORM.id == task_id).first()
        if not task:
            return RelatedTaskInfo(task_id=task_id)
        return RelatedTaskInfo(
            task_id=task.id,
            task_code=getattr(task, "task_code", None),
            task_name=getattr(task, "task_name", None),
            task_status=getattr(task, "status", None),
        )


class BridgeTaskResultLookupPort(TaskResultLookupPort):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, result_id: int) -> Optional[TaskResultORM]:
        return self._db.query(TaskResultORM).filter(TaskResultORM.id == result_id).first()


class BridgeAuditLogLookupPort(AuditLogLookupPort):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, log_id: int) -> Optional[AuditLogORM]:
        return self._db.query(AuditLogORM).filter(AuditLogORM.id == log_id).first()
