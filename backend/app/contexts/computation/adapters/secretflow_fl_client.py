from __future__ import annotations

import json
from urllib import error as url_error
from urllib import request as url_request

from fastapi import HTTPException

from app.core.config import settings


class SecretFlowFLService:
    """
    Alice 节点 SecretFlow 联邦学习训练服务 HTTP 客户端。

    FastAPI 后端不直接运行 SecretFlow，只通过 HTTP 调用 Alice 节点 18181 服务。
    """

    @staticmethod
    def run_flu_fl_train(
        *,
        task_id: str,
        train_mode: str = "horizontal",
        alice_csv: str | None = None,
        bob_csv: str | None = None,
        epochs: int | None = None,
        batch_size: int | None = None,
        learning_rate: float | None = None,
    ) -> dict:
        base_url = settings.SECRETFLOW_FL_SERVICE_URL.rstrip("/")
        url = f"{base_url}/train/flu-fl"

        payload = {
            "task_id": task_id,
            "train_mode": train_mode,
            "alice_csv": alice_csv,
            "bob_csv": bob_csv,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
        }

        # 清理 None，避免覆盖 Alice 端默认值
        payload = {k: v for k, v in payload.items() if v is not None}

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.SECRETFLOW_FL_API_KEY,
        }

        req = url_request.Request(
            url=url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with url_request.urlopen(
                req,
                timeout=settings.SECRETFLOW_FL_TIMEOUT_SECONDS,
            ) as resp:
                resp_body = resp.read().decode("utf-8")
        except url_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联邦训练服务返回异常: HTTP {exc.code}, {error_body}",
            ) from exc
        except url_error.URLError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"无法连接 SecretFlow 联邦训练服务: {exc.reason}",
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail="调用 SecretFlow 联邦训练服务超时",
            ) from exc

        try:
            data = json.loads(resp_body)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联邦训练服务返回非 JSON 内容: {resp_body}",
            ) from exc

        if not isinstance(data, dict):
            raise HTTPException(status_code=502, detail="SecretFlow 联邦训练服务返回格式错误")

        if not data.get("success"):
            raise HTTPException(
                status_code=502,
                detail=f"SecretFlow 联邦训练失败: {data}",
            )

        return data
