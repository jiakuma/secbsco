import request from './request'

export interface StatTemplateItem {
  id: number
  template_code: string
  template_name: string
  agency_id: number | null
  agency_name: string | null
  scenario: string | null
  exec_mode: string | null
  output_type: string | null
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface StatTemplateListParams {
  keyword?: string
  agency_id?: number
  page?: number
  page_size?: number
}

export interface StatTemplateCreateParams {
  template_code: string
  template_name: string
  agency_id?: number
  scenario?: string
  exec_mode?: string
  output_type?: string
  description?: string
}

export interface StatTemplateUpdateParams {
  template_name?: string
  scenario?: string
  exec_mode?: string
  output_type?: string
  description?: string
}

export function getStatTemplateList(params?: StatTemplateListParams) {
  return request.get('/api/stat-templates', { params })
}

export function getStatTemplate(id: number) {
  return request.get(`/api/stat-templates/${id}`)
}

export function createStatTemplate(data: StatTemplateCreateParams) {
  return request.post('/api/stat-templates', data)
}

export function updateStatTemplate(id: number, data: StatTemplateUpdateParams) {
  return request.put(`/api/stat-templates/${id}`, data)
}

export function deleteStatTemplate(id: number) {
  return request.delete(`/api/stat-templates/${id}`)
}