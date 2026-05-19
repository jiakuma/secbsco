// 用户管理相关接口
import request from './request'

export interface UserListParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  agency_id?: number
  role_code?: string
}

export interface UserPayload {
  username?: string
  password?: string
  real_name?: string
  phone?: string
  email?: string
  agency_id?: number | null
  status?: string
}

export interface RoleBindPayload {
  role_code: string
  scope_type: string
  scope_id?: number | null
}

export function getUserList(params?: UserListParams) {
  return request.get('/api/users', { params })
}

export function getUserDetail(userId: number) {
  return request.get(`/api/users/${userId}`)
}

export function createUser(data: UserPayload) {
  return request.post('/api/users', data)
}

export function updateUser(userId: number, data: UserPayload) {
  return request.put(`/api/users/${userId}`, data)
}

export function enableUser(userId: number) {
  return request.post(`/api/users/${userId}/enable`)
}

export function disableUser(userId: number) {
  return request.post(`/api/users/${userId}/disable`)
}

// 兼容旧页面：如果旧页面仍然调用 delete，也可以继续使用
export function deleteUserAsDisable(userId: number) {
  return request.delete(`/api/users/${userId}`)
}

export { deleteUserAsDisable as disableUserByDelete }

export function getUserRoles(userId: number) {
  return request.get(`/api/users/${userId}/roles`)
}

export function bindUserRole(userId: number, data: RoleBindPayload) {
  return request.post(`/api/users/${userId}/roles`, data)
}

export function unbindUserRole(userId: number, bindingId: number) {
  return request.delete(`/api/users/${userId}/roles/${bindingId}`)
}

export function getUserGroups(userId: number) {
  return request.get(`/api/users/${userId}/groups`)
}

export function addUserToGroup(userId: number, data: any) {
  return request.post(`/api/users/${userId}/groups`, data)
}

export function removeUserFromGroup(userId: number, groupId: number) {
  return request.delete(`/api/users/${userId}/groups/${groupId}`)
}

export interface SwitchUserOption {
  id: number
  username: string
  real_name: string
  agency_id: number | null
  agency_name: string | null
  role_code: string | null
  scope_type: string | null
  role_label: string | null
  status: string
}

export function getSwitchUserOptions() {
  return request.get('/api/users/switch-options')
}
