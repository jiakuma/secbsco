import request from './request'

export function getStatTemplateList(params?: any) {
  return request.get('/api/stat-templates', { params })
}