import request from './request'

export interface AgencyQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
}

export function getAgencyList(params?: AgencyQueryParams) {
  return request.get('/api/agencies', { params })
}