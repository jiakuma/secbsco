import request from './request'

export interface NodeQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  agency_id?: number | string
}

export function getNodeList(params?: NodeQueryParams) {
  return request.get('/api/nodes', { params })
}