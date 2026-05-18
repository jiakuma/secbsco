import request from './request'

export interface AgencyListParams {
  keyword?: string
  agency_level?: string
  agency_type?: string
  status?: string
  parent_agency_id?: number
  page?: number
  page_size?: number
}

export interface AgencyPayload {
  agency_code?: string
  agency_name?: string
  agency_type?: string
  agency_level?: string
  parent_agency_id?: number | null
  region_code?: string
  region_name?: string
  contact_person?: string
  contact_phone?: string
  description?: string
  status?: string
}

export function getAgencyList(params?: AgencyListParams) {
  return request.get('/api/agencies', { params })
}

export function getAgencyTree() {
  return request.get('/api/agencies/tree')
}

export function getAgencyDetail(agencyId: number) {
  return request.get(`/api/agencies/${agencyId}`)
}

export function createAgency(data: AgencyPayload) {
  return request.post('/api/agencies', data)
}

export function updateAgency(agencyId: number, data: AgencyPayload) {
  return request.put(`/api/agencies/${agencyId}`, data)
}

export function enableAgency(agencyId: number) {
  return request.post(`/api/agencies/${agencyId}/enable`)
}

export function disableAgency(agencyId: number) {
  return request.post(`/api/agencies/${agencyId}/disable`)
}

export function deleteAgency(agencyId: number) {
  return request.delete(`/api/agencies/${agencyId}`)
}
