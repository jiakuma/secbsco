import request from './request'

export interface TaskQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  task_type?: string
  scenario_code?: string
}

export interface CreateTaskPayload {
  task_code: string
  task_name: string
  template_id?: number | null
  creator_agency_id?: number | null
  stat_start_time?: string
  stat_end_time?: string
  description?: string
  params_json?: Record<string, any>
}

export interface CreateTaskPartyPayload {
  agency_id: number
  node_id: number
  dataset_id: number
  party_role?: string
  field_mapping_json?: Record<string, any>
}

export function getTaskList(params?: TaskQueryParams) {
  return request.get('/api/tasks', { params })
}

export function createTask(data: CreateTaskPayload) {
  return request.post('/api/tasks', data)
}

export function createTaskParty(taskId: number | string, data: CreateTaskPartyPayload) {
  return request.post(`/api/tasks/${taskId}/parties`, data)
}

export function getTaskDetail(taskId: number | string) {
  return request.get(`/api/tasks/${taskId}`)
}

export function updateTask(taskId: number | string, data: Partial<CreateTaskPayload>) {
  return request.put(`/api/tasks/${taskId}`, data)
}

export function updateTaskStatus(taskId: number | string, status: string) {
  return request.put(`/api/tasks/${taskId}/status`, { status })
}

export function runTask(taskId: number | string) {
  return request.post(`/api/tasks/${taskId}/run`, {}, { timeout: 20 * 60 * 1000 })
}

export function getTaskResult(taskId: number | string) {
  return request.get(`/api/tasks/${taskId}/result`)
}

export function anchorTaskResult(taskId: number | string) {
  return request.post(`/api/tasks/${taskId}/chain-anchor`)
}

export function getTaskParties(taskId: number | string) {
  return request.get(`/api/tasks/${taskId}/parties`)
}

export function deleteTaskParty(taskId: number | string, partyId: number | string) {
  return request.delete(`/api/tasks/${taskId}/parties/${partyId}`)
}


