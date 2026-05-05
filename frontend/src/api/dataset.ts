import request from './request'

export function getDatasetList(params?: any) {
  return request.get('/api/datasets', { params })
}