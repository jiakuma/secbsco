"""
区块链锚定服务 - 任务结果自动上链

当前对接 Alice 节点 FISCO Anchor Service：
POST {FISCO_ANCHOR_SERVICE_URL}/anchor/result
请求体：{"task_id": "task_任务ID_result_结果ID", "digest": "结果哈希"}
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.task import Task
from app.models.task_result import TaskResult
from app.models.chain_record import ChainRecord

logger = logging.getLogger(__name__)


class BlockchainAnchorService:
    """区块链锚定服务"""

    @staticmethod
    def anchor_task_result(
        db: Session,
        task_id: int,
        trigger_mode: str = "manual",
    ) -> Dict[str, Any]:
        """
        锚定任务结果到区块链。

        Args:
            db: 数据库会话
            task_id: 任务ID
            trigger_mode: 触发模式，manual / auto

        Returns:
            统一响应格式: {code, message, data}
        """
        try:
            # 1. 查询任务
            task = db.scalar(select(Task).where(Task.id == task_id))
            if not task:
                return {
                    "code": 404,
                    "message": f"任务 {task_id} 不存在",
                    "data": None,
                }

            # 2. 查询最新成功的任务结果
            task_result = db.scalar(
                select(TaskResult)
                .where(
                    TaskResult.task_id == task_id,
                    TaskResult.status == "success",
                )
                .order_by(TaskResult.created_at.desc())
                .limit(1)
            )

            if not task_result:
                return {
                    "code": 400,
                    "message": f"任务 {task_id} 没有成功的结果，无法上链",
                    "data": None,
                }

            if not task_result.result_hash:
                return {
                    "code": 400,
                    "message": f"任务 {task_id} 的结果哈希为空，无法上链",
                    "data": None,
                }

            # 3. 幂等性检查：同一个 result_id + 同一个 result_hash 已成功上链才不重复上链。
            # 说明：task_result 表按 task_id 唯一，同一任务重新执行会复用同一个 result_id，
            # 但 result_hash 会变化。因此幂等判断必须同时比较 content_hash，
            # 否则会把“新结果”误判为“已上链”，导致不会新增 chain_record。
            existing_record = db.scalar(
                select(ChainRecord)
                .where(
                    ChainRecord.biz_type == "task_result",
                    ChainRecord.result_id == task_result.id,
                    ChainRecord.content_hash == task_result.result_hash,
                    ChainRecord.status == "success",
                )
                .limit(1)
            )
            if not existing_record:
                existing_record = db.scalar(
                    select(ChainRecord)
                    .where(
                        ChainRecord.biz_type == "task_result",
                        ChainRecord.biz_id == str(task_result.id),
                        ChainRecord.content_hash == task_result.result_hash,
                        ChainRecord.status == "success",
                    )
                    .limit(1)
                )

            if existing_record:
                BlockchainAnchorService._mark_task_result_success(db, task_result, existing_record)
                return {
                    "code": 200,
                    "message": "该任务结果摘要已成功上链，不重复上链",
                    "data": {
                        "success": True,
                        "task_id": task_id,
                        "result_id": task_result.id,
                        "result_hash": task_result.result_hash,
                        "tx_hash": existing_record.tx_hash,
                        "block_number": existing_record.block_number,
                        "contract_address": existing_record.contract_address,
                        "chain_record_id": existing_record.id,
                        "trigger_mode": trigger_mode,
                        "already_anchored": True,
                    },
                }

            # 4. 准备上链数据。注意：18080 当前真实接口是 /anchor/result，不是 /anchor/save。
            anchor_task_id = BlockchainAnchorService._build_anchor_task_id(task_result)
            timestamp = int(time.time())
            payload = {
                "task_id": anchor_task_id,
                "digest": task_result.result_hash,
                "timestamp": timestamp,
            }

            # 5. 调用 Alice 节点 FISCO Anchor Service
            try:
                result = BlockchainAnchorService._call_fisco_anchor_service(payload)
            except Exception as e:
                error_msg = f"调用FISCO上链服务失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                chain_record = BlockchainAnchorService._create_failed_record(
                    db=db,
                    task_result=task_result,
                    error_message=error_msg,
                    trigger_mode=trigger_mode,
                )
                return {
                    "code": 500,
                    "message": error_msg,
                    "data": {
                        "success": False,
                        "task_id": task_id,
                        "result_id": task_result.id,
                        "result_hash": task_result.result_hash,
                        "error_message": str(e),
                        "chain_record_id": chain_record.id,
                        "trigger_mode": trigger_mode,
                    },
                }

            # 6. 上链成功，保存 chain_record 并回写 task_result
            chain_record = BlockchainAnchorService._create_success_record(
                db=db,
                task_result=task_result,
                anchor_result=result,
                trigger_mode=trigger_mode,
            )

            return {
                "code": 200,
                "message": "任务结果上链成功",
                "data": {
                    "success": True,
                    "task_id": task_id,
                    "result_id": task_result.id,
                    "result_hash": task_result.result_hash,
                    "tx_hash": result.get("tx_hash"),
                    "block_number": result.get("block_number"),
                    "contract_address": result.get("contract_address")
                    or getattr(settings, "FISCO_CONTRACT_ADDRESS", None),
                    "chain_record_id": chain_record.id,
                    "trigger_mode": trigger_mode,
                    "already_anchored": False,
                    "verify_result": result.get("verify_result"),
                },
            }

        except Exception as e:
            logger.exception(f"锚定任务结果时发生异常: {e}")
            db.rollback()
            return {
                "code": 500,
                "message": f"内部服务器错误: {str(e)}",
                "data": None,
            }

    @staticmethod
    def _call_fisco_anchor_service(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 FISCO BCOS 锚定服务。

        注意：Alice 18080 的 /anchor/result 已验证成功的最小请求体只包含
        task_id 和 digest；这里不再主动传 timestamp，也不再附加认证头，
        避免服务端因额外字段或 Header 进入异常分支。
        """
        base_url = getattr(settings, "FISCO_ANCHOR_SERVICE_URL", "http://123.60.109.244:18080").rstrip("/")
        url = f"{base_url}/anchor/result"

        request_body = {
            "task_id": payload["task_id"],
            "digest": payload["digest"],
        }
        headers = {"Content-Type": "application/json"}

        timeout = getattr(settings, "FISCO_ANCHOR_TIMEOUT_SECONDS", 10)
        timeout = timeout if timeout and timeout > 0 else 10

        try:
            response = requests.post(url, json=request_body, headers=headers, timeout=timeout)
            if response.status_code >= 400:
                raise Exception(f"HTTP {response.status_code}, response={response.text}")
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP请求失败: {str(e)}") from e
        except ValueError as e:
            raise Exception(f"上链服务返回非JSON响应: {str(e)}, response={getattr(response, 'text', '')}") from e

        if not isinstance(data, dict):
            raise Exception(f"上链服务返回格式错误: {data}")

        if not data.get("success"):
            raise Exception(f"上链服务返回失败: {data}")

        if data.get("verify_result") is False:
            raise Exception(f"上链后链上校验失败: {data}")

        return data

    @staticmethod
    def _create_success_record(
        db: Session,
        task_result: TaskResult,
        anchor_result: Dict[str, Any],
        trigger_mode: str,
    ) -> ChainRecord:
        """创建成功的链上记录，并回写 task_result。"""
        chain_record = ChainRecord(
            biz_type="task_result",
            # 保持旧接口兼容：biz_id 仍保存 result_id 字符串，便于旧存证列表推导任务。
            biz_id=str(task_result.id),
            content_hash=task_result.result_hash,
            chain_type=anchor_result.get("chain_type") or getattr(settings, "FISCO_CHAIN_TYPE", "fisco_bcos"),
            tx_hash=anchor_result.get("tx_hash"),
            block_number=anchor_result.get("block_number"),
            contract_address=anchor_result.get("contract_address") or getattr(settings, "FISCO_CONTRACT_ADDRESS", None),
            status="success",
            error_message=None,
            **BlockchainAnchorService._get_optional_fields(task_result, trigger_mode, anchor_result),
        )

        db.add(chain_record)
        db.flush()

        BlockchainAnchorService._mark_task_result_success(db, task_result, chain_record)

        db.commit()
        db.refresh(chain_record)
        return chain_record

    @staticmethod
    def _create_failed_record(
        db: Session,
        task_result: TaskResult,
        error_message: str,
        trigger_mode: str,
    ) -> ChainRecord:
        """创建失败的链上记录，并回写 task_result。"""
        chain_record = ChainRecord(
            biz_type="task_result",
            biz_id=str(task_result.id),
            content_hash=task_result.result_hash or "",
            chain_type=getattr(settings, "FISCO_CHAIN_TYPE", "fisco_bcos"),
            tx_hash=None,
            block_number=None,
            contract_address=getattr(settings, "FISCO_CONTRACT_ADDRESS", None),
            status="failed",
            error_message=error_message,
            **BlockchainAnchorService._get_optional_fields(task_result, trigger_mode, None),
        )

        db.add(chain_record)
        db.flush()

        BlockchainAnchorService._mark_task_result_failed(db, task_result)

        db.commit()
        db.refresh(chain_record)
        return chain_record

    @staticmethod
    def _get_optional_fields(
        task_result: TaskResult,
        trigger_mode: str,
        anchor_result: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """获取可选字段，兼容模型字段不存在的情况。"""
        optional_fields: Dict[str, Any] = {}
        now = datetime.now()

        if hasattr(ChainRecord, "created_at"):
            optional_fields["created_at"] = now
        if hasattr(ChainRecord, "updated_at"):
            optional_fields["updated_at"] = now
        if hasattr(ChainRecord, "trigger_mode"):
            optional_fields["trigger_mode"] = trigger_mode
        if hasattr(ChainRecord, "task_id"):
            optional_fields["task_id"] = task_result.task_id
        if hasattr(ChainRecord, "result_id"):
            optional_fields["result_id"] = task_result.id
        if hasattr(ChainRecord, "group_id"):
            optional_fields["group_id"] = getattr(task_result, "group_id", None)
        if hasattr(ChainRecord, "agency_id"):
            optional_fields["agency_id"] = getattr(task_result, "agency_id", None)
        if hasattr(ChainRecord, "anchor_id"):
            optional_fields["anchor_id"] = BlockchainAnchorService._build_anchor_task_id(task_result)
        if hasattr(ChainRecord, "contract_name"):
            optional_fields["contract_name"] = "ResultAnchor"
        if hasattr(ChainRecord, "contract_version"):
            optional_fields["contract_version"] = "1.0"

        if anchor_result is not None:
            if hasattr(ChainRecord, "verify_status"):
                optional_fields["verify_status"] = "success" if anchor_result.get("verify_result") else "failed"
            if hasattr(ChainRecord, "last_verify_time"):
                optional_fields["last_verify_time"] = now
            if hasattr(ChainRecord, "verify_detail_json"):
                optional_fields["verify_detail_json"] = anchor_result
        else:
            if hasattr(ChainRecord, "verify_status"):
                optional_fields["verify_status"] = "failed"
            if hasattr(ChainRecord, "last_verify_time"):
                optional_fields["last_verify_time"] = now

        return optional_fields

    @staticmethod
    def _build_anchor_task_id(task_result: TaskResult) -> str:
        """构造传给 ResultAnchor 合约的 task_id。

        同一 task_result.id 可能因为重新执行任务而产生多个 result_hash。
        因此链上业务ID加入 result_version，避免同一任务结果行的不同版本在链上互相覆盖。
        """
        version = getattr(task_result, "result_version", None) or 1
        return f"task_{task_result.task_id}_result_{task_result.id}_v{version}"

    @staticmethod
    def _mark_task_result_success(db: Session, task_result: TaskResult, chain_record: ChainRecord) -> None:
        """回写任务结果上链成功状态。"""
        now = datetime.now()
        if hasattr(task_result, "anchor_status"):
            task_result.anchor_status = "success"
        if hasattr(task_result, "anchor_time"):
            task_result.anchor_time = now
        if hasattr(task_result, "chain_record_id"):
            task_result.chain_record_id = chain_record.id
        if hasattr(task_result, "updated_at"):
            task_result.updated_at = now
        db.add(task_result)
        db.flush()

    @staticmethod
    def _mark_task_result_failed(db: Session, task_result: TaskResult) -> None:
        """回写任务结果上链失败状态。"""
        now = datetime.now()
        if hasattr(task_result, "anchor_status"):
            task_result.anchor_status = "failed"
        if hasattr(task_result, "updated_at"):
            task_result.updated_at = now
        db.add(task_result)
        db.flush()

    @staticmethod
    def trigger_auto_anchor_on_task_success(
        db: Session,
        task_id: int,
    ) -> None:
        """
        任务成功时触发自动上链。
        此方法应在任务成功执行后被调用。
        """
        try:
            if not getattr(settings, "AUTO_CHAIN_ANCHOR_ON_TASK_SUCCESS", True):
                logger.info(f"自动上链功能已关闭，跳过任务 {task_id} 的自动上链")
                return

            result = BlockchainAnchorService.anchor_task_result(db, task_id, "auto")

            if result.get("code") == 200 and result.get("data", {}).get("success"):
                logger.info(f"任务 {task_id} 结果自动上链成功: {result['data'].get('tx_hash')}")
            else:
                logger.warning(f"任务 {task_id} 结果自动上链失败: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"任务 {task_id} 自动上链触发异常: {e}", exc_info=True)
