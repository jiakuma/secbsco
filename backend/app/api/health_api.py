from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.utils.response import success, fail

router = APIRouter(prefix="/api/health", tags=["健康检查"])


@router.get("")
def health_check():
    return success({
        "status": "ok",
        "service": "biosecurity-backend"
    })


@router.get("/db")
def db_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return success({
            "database": "connected"
        })
    except Exception as e:
        return fail(
            message=f"database connection failed: {str(e)}",
            code=500
        )