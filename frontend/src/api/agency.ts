import request from './request'

export function getAgencyList(params?: any) {
  return request.get('/api/agencies', { params })
}