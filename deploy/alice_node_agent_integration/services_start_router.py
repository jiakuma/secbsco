"""
Node-Agent 服务启动接口模块

将此模块集成到现有 Alice node-agent (19090) 中。

集成方式：
1. 复制本文件到 node-agent 项目目录
2. 在主 app 中导入并挂载路由：
   from services_start_router import router as services_router
   app.include_router(services_router)
"""

import subprocess
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests

router = APIRouter()


class ServiceStartRequest(BaseModel):
    service_code: str


SERVICE_WHITELIST = {
    "bio_task_runtime": {
        "port": 18190,
        "health_url": "http://127.0.0.1:18190/health",
        "start_command": """
cd /opt/bio-task-runtime
mkdir -p /opt/bio-task-runtime/logs
nohup /root/miniconda3/envs/sf113/bin/python -m uvicorn bio_task_runtime_service:app \
  --host 0.0.0.0 \
  --port 18190 \
  > /opt/bio-task-runtime/logs/bio_task_runtime_18190.log 2>&1 &
""",
        "check_port_command": "ss -lntp | grep 18190",
        "description": "Bio Task Runtime 服务（T2 时空轨迹预测）",
    },
}


def check_port_listening(port: int) -> bool:
    try:
        result = subprocess.run(
            f"ss -lntp | grep {port}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def check_service_health(health_url: str, timeout: int = 3) -> bool:
    try:
        resp = requests.get(health_url, timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def start_service_by_code(service_code: str) -> dict:
    if service_code not in SERVICE_WHITELIST:
        return {
            "success": False,
            "message": f"服务不在白名单中：{service_code}",
            "allowed_services": list(SERVICE_WHITELIST.keys()),
        }

    service = SERVICE_WHITELIST[service_code]
    port = service["port"]
    health_url = service["health_url"]

    if check_port_listening(port):
        if check_service_health(health_url):
            return {
                "success": True,
                "message": "bio-task-runtime 已在运行",
                "service_code": service_code,
                "port": port,
                "already_running": True,
            }

    start_cmd = service["start_command"]

    try:
        subprocess.run(
            start_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "启动命令执行超时",
            "service_code": service_code,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"启动命令执行失败：{str(e)}",
            "service_code": service_code,
        }

    time.sleep(3)

    for i in range(5):
        if check_service_health(health_url):
            return {
                "success": True,
                "message": f"bio-task-runtime 启动成功",
                "service_code": service_code,
                "port": port,
                "already_running": False,
            }
        time.sleep(2)

    return {
        "success": False,
        "message": "bio-task-runtime 启动超时，请检查日志",
        "service_code": service_code,
        "log_path": "/opt/bio-task-runtime/logs/bio_task_runtime_18190.log",
    }


@router.post("/services/start")
async def services_start(request: ServiceStartRequest):
    result = start_service_by_code(request.service_code)
    status_code = 200 if result.get("success") else 400
    return JSONResponse(content=result, status_code=status_code)


@router.get("/services")
async def list_services():
    return {
        "services": [
            {
                "code": code,
                "port": info["port"],
                "description": info["description"],
                "listening": check_port_listening(info["port"]),
                "healthy": check_service_health(info["health_url"]),
            }
            for code, info in SERVICE_WHITELIST.items()
        ]
    }
