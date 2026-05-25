from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.chain_record import ChainRecord as ChainRecordORM
from ..domain.models import ChainRecordInfo, RelatedTaskInfo
from ..domain.ports import ChainRecordRepository, RelatedTaskPort


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
            from app.services.task_result_service import TaskResultService
            result = TaskResultService.get_result_by_id(db=self._db, result_id=biz_id_int)
            task_id = getattr(result, "task_id", None) if result else None
        elif biz_type == "audit_log":
            from app.services.audit_log_service import AuditLogService
            log = AuditLogService.get_log_by_id(db=self._db, log_id=biz_id_int)
            task_id = getattr(log, "task_id", None) if log else None

        if not task_id:
            return None

        try:
            from app.services.task_service import get_task_or_404
            task = get_task_or_404(db=self._db, task_id=task_id)
        except Exception:
            return RelatedTaskInfo(task_id=task_id)

        return RelatedTaskInfo(
            task_id=getattr(task, "id", task_id),
            task_code=getattr(task, "task_code", None),
            task_name=getattr(task, "task_name", None),
            task_status=getattr(task, "status", None),
        )
