import request from './request'

export function getNodeList(params?: any) {
  return request.get('/api/nodes', { params })
}