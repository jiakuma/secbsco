from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard_schema import (
    DashboardSummaryResponse,
    RecentAuditLogsResponse,
    RecentChainRecordsResponse,
    RecentResultsResponse,
    RecentTasksResponse,
)
from app.services import dashboard_service


router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="首页统计卡片",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_dashboard_summary(db)

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get(
    "/recent-tasks",
    response_model=RecentTasksResponse,
    summary="最近联合统计任务",
)
def get_recent_tasks(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_recent_tasks(db, limit=limit)

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get(
    "/recent-results",
    response_model=RecentResultsResponse,
    summary="最近联合统计结果",
)
def get_recent_results(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_recent_results(db, limit=limit)

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get(
    "/recent-audit-logs",
    response_model=RecentAuditLogsResponse,
    summary="最近审计日志",
)
def get_recent_audit_logs(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_recent_audit_logs(db, limit=limit)

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }


@router.get(
    "/recent-chain-records",
    response_model=RecentChainRecordsResponse,
    summary="最近链上存证记录",
)
def get_recent_chain_records(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
):
    data = dashboard_service.get_recent_chain_records(db, limit=limit)

    return {
        "code": 0,
        "message": "success",
        "data": data,
    }