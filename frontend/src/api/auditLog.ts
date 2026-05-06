import request from './request'

export interface AuditLogQueryParams {
  page?: number
  page_size?: number
  task_id?: number | string
  agency_id?: number | string
  operator_user_id?: number | string
  operation_type?: string
  object_type?: string
  object_id?: string | number
}

export function getAuditLogList(params?: AuditLogQueryParams) {
  return request.get('/api/audit-logs', { params })
}

export function getAuditLogDetail(logId: number | string) {
  return request.get(`/api/audit-logs/${logId}`)
}
