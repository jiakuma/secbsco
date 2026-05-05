import request from './request'

export interface DatasetQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  agency_id?: number | string
}

export function getDatasetList(params?: DatasetQueryParams) {
  return request.get('/api/datasets', { params })
}