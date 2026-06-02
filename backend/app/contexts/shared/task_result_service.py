import hashlib
import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.task_result import TaskResult


class TaskResultService:

    @staticmethod
    def list_results(
        db: Session,
        task_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(TaskResult)

        if task_id:
            query = query.filter(TaskResult.task_id == task_id)

        if status:
            query = query.filter(TaskResult.status == status)

        total = query.count()

        items = (
            query
            .order_by(TaskResult.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_result_by_id(
        db: Session,
        result_id: int
    ) -> Optional[TaskResult]:
        return (
            db.query(TaskResult)
            .filter(TaskResult.id == result_id)
            .first()
        )

    @staticmethod
    def get_result_by_task_id(
        db: Session,
        task_id: int
    ) -> Optional[TaskResult]:
        return (
            db.query(TaskResult)
            .filter(TaskResult.task_id == task_id)
            .first()
        )

    @staticmethod
    def generate_result_hash(result_json: dict) -> str:
        result_text = json.dumps(
            result_json,
            ensure_ascii=False,
            sort_keys=True
        )
        return hashlib.sha256(result_text.encode("utf-8")).hexdigest()

    @staticmethod
    def build_mock_result() -> tuple[dict, dict, str]:
        result_json = {
            "case_count": 1280,
            "unique_patient_count": 1156,
            "positive_count": 236,
            "positive_rate": 0.1844
        }

        metrics_json = {
            "metrics": [
                {
                    "code": "case_count",
                    "name": "病例数",
                    "value": 1280,
                    "unit": "人次"
                },
                {
                    "code": "unique_patient_count",
                    "name": "去重后人数",
                    "value": 1156,
                    "unit": "人"
                },
                {
                    "code": "positive_count",
                    "name": "阳性数",
                    "value": 236,
                    "unit": "人"
                },
                {
                    "code": "positive_rate",
                    "name": "阳性率",
                    "value": 0.1844,
                    "unit": "%"
                }
            ],
            "summary": {
                "description": "Mock 联合统计结果",
                "calculation_mode": "mock"
            }
        }

        result_hash = TaskResultService.generate_result_hash(result_json)

        return result_json, metrics_json, result_hash

    @staticmethod
    def create_or_update_mock_result(
        db: Session,
        task_id: int
    ) -> TaskResult:
        result_json, metrics_json, result_hash = TaskResultService.build_mock_result()

        existed = TaskResultService.get_result_by_task_id(
            db=db,
            task_id=task_id
        )

        if existed:
            existed.result_json = result_json
            existed.metrics_json = metrics_json
            existed.result_hash = result_hash
            existed.status = "success"
            existed.error_message = None

            db.commit()
            db.refresh(existed)

            return existed

        result = TaskResult(
            task_id=task_id,
            result_json=result_json,
            metrics_json=metrics_json,
            result_hash=result_hash,
            status="success",
            error_message=None,
        )

        db.add(result)
        db.commit()
        db.refresh(result)

        return result

    @staticmethod
    def build_result_info(result: TaskResult) -> dict:
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