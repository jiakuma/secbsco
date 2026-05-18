import request from './request'

export interface NodeListParams {
  keyword?: string
  agency_id?: number
  status?: string
  node_type?: string
  page?: number
  page_size?: number
}

export interface NodePayload {
  node_code?: string
  node_name?: string
  agency_id?: number
  node_type?: string
  node_capabilities?: string[]
  node_role?: string
  service_url?: string
  endpoint?: string
  internal_ip?: string
  public_ip?: string
  health_check_url?: string
  ray_address?: string
  anchor_service_url?: string
  contract_address?: string
  status?: string
  description?: string
}

export function getNodeList(params?: NodeListParams) {
  return request.get('/api/nodes', { params })
}

export function getNodeDetail(nodeId: number) {
  return request.get(`/api/nodes/${nodeId}`)
}

export function createNode(data: NodePayload) {
  return request.post('/api/nodes', data)
}

export function updateNode(nodeId: number, data: NodePayload) {
  return request.put(`/api/nodes/${nodeId}`, data)
}

export function enableNode(nodeId: number) {
  return request.post(`/api/nodes/${nodeId}/enable`)
}

export function disableNode(nodeId: number) {
  return request.post(`/api/nodes/${nodeId}/disable`)
}

export function updateNodeStatus(nodeId: number, status: string) {
  return request.put(`/api/nodes/${nodeId}/status`, { status })
}

export function deleteNode(nodeId: number) {
  return request.delete(`/api/nodes/${nodeId}`)
}

export function checkNode(nodeId: number) {
  return request.post(`/api/nodes/${nodeId}/check`)
}

export function activateNode(nodeId: number) {
  return request.post(`/api/nodes/${nodeId}/activate`)
}

export function deactivateNode(nodeId: number) {
  return request.post(`/api/nodes/${nodeId}/deactivate`)
}