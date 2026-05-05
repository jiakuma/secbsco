import request from './request'

export interface ChainRecordQueryParams {
  page?: number
  page_size?: number
  biz_type?: string
  biz_id?: string
  status?: string
}

export function getChainRecordList(params?: ChainRecordQueryParams) {
  return request.get('/api/chain-records', { params })
}

export function getChainRecordDetail(recordId: number | string) {
  return request.get(`/api/chain-records/${recordId}`)
}