import request from './request'

export interface DatasetItem {
  id: number
  dataset_code: string
  dataset_name: string
  agency_id: number
  agency_name: string | null
  node_id: number | null
  node_name: string | null
  data_type: string | null
  data_location: string | null
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DatasetQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  agency_id?: number
}

export interface DatasetCreateParams {
  dataset_code: string
  dataset_name: string
  agency_id: number
  node_id?: number
  data_type?: string
  data_location?: string
  description?: string
}

export interface DatasetUpdateParams {
  dataset_name?: string
  node_id?: number
  data_type?: string
  data_location?: string
  description?: string
}

export function getDatasetList(params?: DatasetQueryParams) {
  return request.get('/api/datasets', { params })
}

export function getDataset(id: number) {
  return request.get(`/api/datasets/${id}`)
}

export function createDataset(data: DatasetCreateParams) {
  return request.post('/api/datasets', data)
}

export function updateDataset(id: number, data: DatasetUpdateParams) {
  return request.put(`/api/datasets/${id}`, data)
}

export function deleteDataset(id: number) {
  return request.delete(`/api/datasets/${id}`)
}