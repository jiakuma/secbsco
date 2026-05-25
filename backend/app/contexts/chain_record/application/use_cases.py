from typing import Optional
from dataclasses import asdict
from ..domain.ports import ChainRecordRepository, RelatedTaskPort
from ..domain.models import ChainRecordInfo, RelatedTaskInfo
from ..domain.exceptions import ChainRecordNotFoundError, raise_chain_record_not_found
from .dtos import ChainRecordDTO, ChainRecordPageDTO


def _to_dto(info: ChainRecordInfo, related_task: Optional[RelatedTaskInfo] = None) -> ChainRecordDTO:
    related_dict = asdict(related_task) if related_task else None
    related_task_id = related_task.task_id if related_task else None
    return ChainRecordDTO(
        id=info.id,
        biz_type=info.biz_type,
        biz_id=info.biz_id,
        content_hash=info.content_hash,
        chain_type=info.chain_type,
        tx_hash=info.tx_hash,
        block_number=info.block_number,
        contract_address=info.contract_address,
        status=info.status,
        error_message=info.error_message,
        created_at=info.created_at,
        related_task=related_dict,
        related_task_id=related_task_id,
    )


class ListChainRecordsUseCase:
    def __init__(self, repo: ChainRecordRepository, related_task_port: RelatedTaskPort):
        self._repo = repo
        self._related_task_port = related_task_port

    def execute(
        self,
        biz_type: Optional[str] = None,
        biz_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> ChainRecordPageDTO:
        total, items = self._repo.list_records(
            biz_type=biz_type, biz_id=biz_id, status=status, page=page, page_size=page_size
        )
        dtos = []
        for info in items:
            related = self._related_task_port.build_related_task(info.biz_type, info.biz_id)
            dtos.append(_to_dto(info, related))
        return ChainRecordPageDTO(total=total, page=page, page_size=page_size, items=dtos)


class GetChainRecordUseCase:
    def __init__(self, repo: ChainRecordRepository, related_task_port: RelatedTaskPort):
        self._repo = repo
        self._related_task_port = related_task_port

    def execute(self, record_id: int) -> ChainRecordDTO:
        info = self._repo.get_by_id(record_id)
        if not info:
            raise_chain_record_not_found(record_id)
        related = self._related_task_port.build_related_task(info.biz_type, info.biz_id)
        return _to_dto(info, related)
