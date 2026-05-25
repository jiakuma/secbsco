from fastapi import HTTPException


class AuditLogNotFoundError(Exception):
    pass


def raise_audit_log_not_found(log_id: int):
    raise HTTPException(status_code=404, detail="审计日志不存在")
