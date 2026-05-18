from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import (
    health_api,
    auth_api,
    user_api,
    group_api,
    agency_api,
    node_api,
    dataset_api,
    stat_template_api,
    task_api,
    task_result_api,
    audit_log_api,
    chain_record_api,
    dashboard_api,
)


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
app.include_router(auth_api.router)
app.include_router(user_api.router)
app.include_router(group_api.router)
app.include_router(agency_api.router)
app.include_router(node_api.router)
app.include_router(dataset_api.router)
app.include_router(stat_template_api.router)
app.include_router(task_api.router)
app.include_router(task_result_api.router)
app.include_router(audit_log_api.router)
app.include_router(chain_record_api.router)
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