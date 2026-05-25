from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import (
    health_api,
    dashboard_api,
)
from app.contexts.task.adapters.api import router as task_router
from app.contexts.task.adapters.api import result_router as task_result_router
from app.contexts.audit_log.adapters.api import router as audit_log_router
from app.contexts.chain_record.adapters.api import router as chain_record_router
from app.contexts.agency.adapters import router as agency_router
from app.contexts.identity.adapters.auth_api import router as auth_router
from app.contexts.identity.adapters.user_api import router as user_router
from app.contexts.node.adapters.api import router as node_router
from app.contexts.dataset.adapters.api import router as dataset_router
from app.contexts.template.adapters.api import router as template_router
from app.contexts.group.adapters.api import router as group_router


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
    version="0.1.0",
    description="生物安全数据联合统计系统后端服务",
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_api.router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(group_router)
app.include_router(agency_router)
app.include_router(node_router)
app.include_router(dataset_router)
app.include_router(template_router)
app.include_router(task_router)
app.include_router(task_result_router)
app.include_router(audit_log_router)
app.include_router(chain_record_router)
app.include_router(dashboard_api.router)

@app.get("/")
def root():
    return {
        "code": 0,
        "message": "Biosecurity Federated Statistics Backend is running",
        "data": {
            "docs": "/docs",
            "health": "/api/health",
            "db_health": "/api/health/db"
        }
    }