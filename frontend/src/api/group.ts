/**
 * 群组管理 API - 第4阶段完整接口
 */
import request from './request'

/** 群组列表查询参数 */
export interface GroupListParams {
  keyword?: string
  status?: string
  approval_status?: string
  lead_agency_id?: number
  category?: string
  region_code?: string
  page?: number
  page_size?: number
}

/** 群组列表项 */
export interface GroupItem {
  id: number
  group_code: string
  group_name: string
  group_level: string
  region_code: string | null
  region_name: string | null
  lead_agency_id: number
  lead_agency_name: string | null
  status: string
  approval_status: string
  approval_required: boolean
  created_by: number
  created_by_name: string | null
  created_at: string | null
  member_count: number
  user_count: number
  node_count: number
  task_count: number
  my_relation: string
  can_manage: boolean
  can_approve: boolean
  can_delete: boolean
  need_delete_approval: boolean
  can_approve_delete: boolean
}

/** 群组详情 */
export interface GroupDetail {
  id: number
  group_code: string
  group_name: string
  group_level: string
  region_code: string | null
  region_name: string | null
  lead_agency_id: number
  lead_agency_name: string | null
  description: string | null
  status: string
  approval_status: string
  approval_required: boolean
  approval_agency_id: number | null
  creator_agency_id: number | null
  created_by: number
  created_by_name: string | null
  created_at: string | null
  updated_at: string | null
  summary: {
    member_count: number
    user_count: number
    admin_count: number
    governor_count: number
    node_count: number
    task_count: number
    result_count: number
    chain_record_count: number
  }
}

/** 创建群组参数 */
export interface GroupCreateParams {
  group_code: string
  group_name: string
  group_level: string
  region_code?: string
  region_name?: string
  lead_agency_id: number
  member_agency_ids?: number[]
  description?: string
}

/** 更新群组参数 */
export interface GroupUpdateParams {
  group_name?: string
  group_level?: string
  region_code?: string
  region_name?: string
  description?: string
}

/** 生命周期日志项 */
export interface LifecycleLogItem {
  id: number
  group_id: number
  event_type: string
  before_status: string | null
  after_status: string | null
  operator_user_id: number | null
  operator_name: string | null
  reason: string | null
  detail_json: Record<string, any> | null
  created_at: string | null
}

/** 群组成员机构 */
export interface GroupMemberItem {
  id: number
  group_id: number
  agency_id: number
  agency_name: string | null
  member_role: string
  is_lead: boolean
  join_status: string
  joined_at: string | null
}

/** 群组用户 */
export interface GroupUserItem {
  user_id: number
  username: string
  real_name: string | null
  agency_id: number | null
  agency_name: string | null
  join_status: string
  roles: { role_code: string; scope_type: string; scope_id: number }[]
}

/** 群组节点 */
export interface GroupNodeItem {
  group_node_id: number
  node_id: number
  node_code: string
  node_name: string
  agency_id: number
  agency_name: string | null
  node_type: string
  node_usage_role: string
  auth_status: string
  node_status: string
  node_load_status: string
}

/** 可授权节点 */
export interface AvailableNodeItem {
  node_id: number
  node_code: string
  node_name: string
  agency_id: number
  agency_name: string | null
  node_type: string
  node_status: string
  authorized: boolean
}

// ============================================================
// 群组基础 API
// ============================================================

/** 获取群组列表 */
export function getGroupList(params: GroupListParams) {
  return request.get('/api/groups', { params })
}

/** 获取群组详情 */
export function getGroupDetail(groupId: number) {
  return request.get(`/api/groups/${groupId}`)
}

/** 创建群组 */
export function createGroup(data: GroupCreateParams) {
  return request.post('/api/groups', data)
}

/** 更新群组基础信息 */
export function updateGroup(groupId: number, data: GroupUpdateParams) {
  return request.put(`/api/groups/${groupId}`, data)
}

// ============================================================
// 审批 API
// ============================================================

/** 审批通过 */
export function approveGroup(groupId: number, data: { remark?: string }) {
  return request.post(`/api/groups/${groupId}/approve`, data)
}

/** 驳回 */
export function rejectGroup(groupId: number, data: { reason: string }) {
  return request.post(`/api/groups/${groupId}/reject`, data)
}

// ============================================================
// 生命周期日志
// ============================================================

/** 获取群组生命周期日志 */
export function getGroupLifecycleLogs(groupId: number, params?: { event_type?: string; page?: number; page_size?: number }) {
  return request.get(`/api/groups/${groupId}/lifecycle-logs`, { params })
}

// ============================================================
// 成员机构 API
// ============================================================

/** 获取群组成员机构 */
export function getGroupMembers(groupId: number) {
  return request.get(`/api/groups/${groupId}/members`)
}

/** 添加成员机构 */
export function addGroupMember(groupId: number, data: { agency_id: number; member_type?: string; remark?: string }) {
  return request.post(`/api/groups/${groupId}/members`, data)
}

/** 移除成员机构 */
export function removeGroupMember(groupId: number, agencyId: number) {
  return request.delete(`/api/groups/${groupId}/members/${agencyId}`)
}

// ============================================================
// 群组用户 API
// ============================================================

/** 获取群组用户 */
export function getGroupUsers(groupId: number) {
  return request.get(`/api/groups/${groupId}/users`)
}

/** 添加群组用户 */
export function addGroupUser(groupId: number, data: { user_id: number; role_code: string; remark?: string }) {
  return request.post(`/api/groups/${groupId}/users`, data)
}

/** 修改群组用户角色 */
export function updateGroupUserRole(groupId: number, userId: number, data: { role_code: string }) {
  return request.put(`/api/groups/${groupId}/users/${userId}/role`, data)
}

/** 移出群组用户 */
export function removeGroupUser(groupId: number, userId: number) {
  return request.delete(`/api/groups/${groupId}/users/${userId}`)
}

// ============================================================
// 群组节点 API
// ============================================================

/** 获取群组已授权节点 */
export function getGroupNodes(groupId: number, params?: { node_type?: string; node_usage_role?: string; auth_status?: string }) {
  return request.get(`/api/groups/${groupId}/nodes`, { params })
}

/** 获取群组可授权节点 */
export function getAvailableGroupNodes(groupId: number) {
  return request.get(`/api/groups/${groupId}/available-nodes`)
}

/** 授权节点给群组 */
export function addGroupNode(groupId: number, data: { node_id: number; remark?: string }) {
  return request.post(`/api/groups/${groupId}/nodes`, data)
}

/** 取消节点授权 */
export function removeGroupNode(groupId: number, nodeId: number) {
  return request.delete(`/api/groups/${groupId}/nodes/${nodeId}`)
}

/** 申请删除群组 */
export function requestDeleteGroup(groupId: number) {
  return request.post(`/api/groups/${groupId}/delete-request`)
}

/** 审批通过删除群组 */
export function approveDeleteGroup(groupId: number) {
  return request.post(`/api/groups/${groupId}/delete-approve`)
}

/** 驳回删除群组申请 */
export function rejectDeleteGroup(groupId: number, data: { reason: string }) {
  return request.post(`/api/groups/${groupId}/delete-reject`, data)
}
