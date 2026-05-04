import request from './request'

export function getDashboardSummaryApi() {
  return request.get('/api/dashboard/summary')
}

export function getRecentTasksApi(limit = 5) {
  return request.get('/api/dashboard/recent-tasks', {
    params: { limit },
  })
}

export function getRecentResultsApi(limit = 5) {
  return request.get('/api/dashboard/recent-results', {
    params: { limit },
  })
}

export function getRecentAuditLogsApi(limit = 5) {
  return request.get('/api/dashboard/recent-audit-logs', {
    params: { limit },
  })
}

export function getRecentChainRecordsApi(limit = 5) {
  return request.get('/api/dashboard/recent-chain-records', {
    params: { limit },
  })
}