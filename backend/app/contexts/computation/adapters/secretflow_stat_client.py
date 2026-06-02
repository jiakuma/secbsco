from __future__ import annotations

"""
FastAPI 后端侧 SecretFlow 联合统计调用服务。

注意：
- 当前 Windows 本地 FastAPI 不直接 import secretflow；
- 这里仅通过 HTTP 调用 Alice 节点上的 alice_secretflow_stat_service；
- 真实 SecretFlow / Ray / SPU 计算发生在 Alice 节点。
"""

import json
from urllib import error as url_error
from urllib import request as url_request

from fastapi import HTTPException

from app.core.config import settings


class SecretFlowStatService:
    @staticmethod
    def run_flu_stat(
        *,
        task_id: str,
        start_date: str,
        end_date: str,
        syndrome_type: str,
        alice_csv: str | None = None,
        bob_csv: str | None = None,
    ) -> dict:
        """
        调用 Alice SecretFlow 联合统计服务，返回 result/result_json/result_hash。
        """
        base_url = settings.SECRETFLOW_STAT_SERVICE_URL.rstrip("/")
        url = f"{base_url}/run/flu-stat"

        payload = {
            "task_id": task_id,
            "start_date": start_date,
            "end_date": end_date,
            "syndrome_type": syndrome_type,
            "alice_csv": alice_csv or settings.SECRETFLOW_ALICE_CSV,
            "bob_csv": bob_csv or settings.SECRETFLOW_BOB_CSV,
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.SECRETFLOW_STAT_API_KEY,
        }

        req = url_request.Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with url_request.urlopen(req, timeout=settings.SECRETFLOW_STAT_TIMEOUT_SECONDS) as resp:
                resp_body = resp.read().decode("utf-8")
        except url_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联合统计服务返回异常: HTTP {exc.code}, {error_body}",
            ) from exc
        except url_error.URLError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"无法连接 SecretFlow 联合统计服务: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="调用 SecretFlow 联合统计服务超时",
            ) from exc

        try:
            data = json.loads(resp_body)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联合统计服务返回非 JSON 内容: {resp_body}",
            ) from exc

        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="SecretFlow 联合统计服务返回格式错误")

        if not data.get("success"):
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联合统计执行失败: {data}",
            )

        result = data.get("result")
        result_hash = data.get("result_hash")

        if not isinstance(result, dict) or not result_hash:
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联合统计服务缺少 result 或 result_hash: {data}",
            )

        return data
