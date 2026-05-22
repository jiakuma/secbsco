<template>
  <div class="group-detail-page" v-loading="pageLoading">
    <template v-if="groupDetail">
      <!-- 基础信息卡片 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <el-button type="default" size="small" @click="goBack" class="back-btn">
                <span class="back-icon"></span> 返回列表
              </el-button>
              <span class="card-title">{{ groupDetail.group_name }}</span>
            </div>
            <div class="header-right">
              <el-tag :type="statusTagType(groupDetail.status)" size="default">
                {{ statusLabel(groupDetail.status) }}
              </el-tag>
              <el-tag v-if="groupDetail.approval_status && groupDetail.approval_status !== 'none'"
                      :type="approvalStatusType(groupDetail.approval_status)" size="default">
                {{ approvalStatusLabel(groupDetail.approval_status) }}
              </el-tag>
              <el-button
                type="success"
                size="small"
                @click="goToTaskManagement"
              >
                进入任务管理
              </el-button>
              <el-button
                v-if="canEdit"
                type="primary"
                size="small"
                @click="showEditDialog"
              >
                编辑
              </el-button>
            </div>
          </div>
        </template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="群组编码">{{ groupDetail.group_code }}</el-descriptions-item>
          <el-descriptions-item label="群组层级">{{ groupDetail.group_level }}</el-descriptions-item>
          <el-descriptions-item label="牵头机构">{{ groupDetail.lead_agency_name }}</el-descriptions-item>
          <el-descriptions-item label="区域编码">{{ groupDetail.region_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="区域名称">{{ groupDetail.region_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ groupDetail.created_by_name }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ groupDetail.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ groupDetail.updated_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="3">{{ groupDetail.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stat-row">
        <el-col :xs="12" :sm="8" :md="4" :lg="4" v-for="stat in statCards" :key="stat.label">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Tab 面板 -->
      <el-card class="tab-card">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <!-- 群机构 Tab（一期只读展示） -->
          <el-tab-pane label="群机构" name="members">
            <el-table :data="memberList" v-loading="membersLoading" border stripe>
              <el-table-column prop="agency_name" label="机构名称" min-width="200" />
              <el-table-column prop="member_role" label="成员角色" width="120">
                <template #default="{ row }">
                  <el-tag size="small">{{ memberRoleLabel(row.member_role) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="牵头机构" width="100" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_lead" type="danger" size="small">是</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="join_status" label="加入状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="joinStatusType(row.join_status)" size="small">
                    {{ joinStatusLabel(row.join_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="joined_at" label="加入时间" width="170" />
            </el-table>
          </el-tab-pane>

          <!-- 群用户 Tab（一期只读展示，基于成员机构自动归属） -->
          <el-tab-pane label="群用户" name="users">
            <div class="tab-toolbar">
              <span class="readonly-hint">成员机构下所有已启用用户自动归属该群组</span>
            </div>
            <el-table :data="userList" v-loading="usersLoading" border stripe>
              <el-table-column prop="username" label="用户名" width="120" />
              <el-table-column prop="real_name" label="真实姓名" width="120" />
              <el-table-column prop="agency_name" label="所属机构" min-width="160" />
              <el-table-column prop="user_status" label="用户状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.user_status === 'active' ? 'success' : 'danger'" size="small">
                    {{ row.user_status === 'active' ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 群节点 Tab -->
          <el-tab-pane label="群节点" name="nodes">
            <div class="tab-toolbar" v-if="canManageNodes">
              <el-button type="primary" size="small" @click="showAddNodeDialog">授权节点</el-button>
            </div>
            <el-table :data="nodeList" v-loading="nodesLoading" border stripe>
              <el-table-column prop="node_code" label="节点编码" width="180" />
              <el-table-column prop="node_name" label="节点名称" min-width="180" />
              <el-table-column prop="agency_name" label="所属机构" min-width="160" />
              <el-table-column prop="node_type" label="节点类型" width="120">
                <template #default="{ row }">
                  <el-tag size="small">{{ nodeTypeLabel(row.node_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="auth_status" label="授权状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="authStatusType(row.auth_status)" size="small">
                    {{ authStatusLabel(row.auth_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="canManage" label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="row.auth_status === 'active'"
                    type="danger"
                    link
                    size="small"
                    @click="handleRemoveNode(row)"
                  >
                    取消授权
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 群数据 Tab -->
          <el-tab-pane label="群数据" name="datasets">
            <div class="tab-toolbar" v-if="canManage">
              <el-button type="primary" size="small" @click="showAddDatasetDialog">授权数据集</el-button>
            </div>
            <el-table :data="datasetList" v-loading="datasetsLoading" border stripe>
              <el-table-column prop="dataset_name" label="数据集名称" min-width="180" />
              <el-table-column prop="dataset_code" label="数据集编码" width="180" />
              <el-table-column prop="agency_name" label="所属机构" min-width="160" />
              <el-table-column label="数据类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.data_type || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="data_location" label="数据位置" min-width="200" show-overflow-tooltip />
              <el-table-column v-if="canManage" label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button type="danger" link size="small" @click="handleRemoveDataset(row)">取消授权</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 群模板 Tab -->
          <el-tab-pane label="群模板" name="templates">
            <div class="tab-toolbar" v-if="canManage">
              <el-button type="primary" size="small" @click="showAddTemplateDialog">授权模板</el-button>
            </div>
            <el-table :data="templateList" v-loading="templatesLoading" border stripe>
              <el-table-column prop="template_name" label="模板名称" min-width="180" />
              <el-table-column prop="template_code" label="模板编码" width="180" />
              <el-table-column prop="agency_name" label="所属机构" min-width="160" />
              <el-table-column label="适用场景" width="140">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.scenario || '-' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="执行方式" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.exec_mode === 'auto' ? '自动' : '手动' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column v-if="canManage" label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button type="danger" link size="small" @click="handleRemoveTemplate(row)">取消授权</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 生命周期日志 Tab -->
          <el-tab-pane label="生命周期日志" name="lifecycle">
            <el-table :data="lifecycleList" v-loading="lifecycleLoading" border stripe>
              <el-table-column prop="event_type" label="事件类型" width="150">
                <template #default="{ row }">
                  <el-tag size="small">{{ eventTypeLabel(row.event_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="before_status" label="变更前状态" width="120" />
              <el-table-column prop="after_status" label="变更后状态" width="120" />
              <el-table-column prop="operator_name" label="操作人" width="120" />
              <el-table-column prop="reason" label="原因" min-width="200" show-overflow-tooltip />
              <el-table-column prop="created_at" label="创建时间" width="170" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>

    <!-- 编辑群组弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑群组基础信息" width="600px" :close-on-click-modal="false">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px">
        <el-form-item label="群组名称" prop="group_name">
          <el-input v-model="editForm.group_name" placeholder="请输入群组名称" maxlength="128" />
        </el-form-item>
        <el-form-item label="群组层级" prop="group_level">
          <el-select v-model="editForm.group_level" style="width: 100%">
            <el-option label="县级" value="county" />
            <el-option label="市级" value="city" />
            <el-option label="省级" value="province" />
            <el-option label="国家级" value="national" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域编码">
          <el-input v-model="editForm.region_code" placeholder="请输入区域编码" maxlength="64" />
        </el-form-item>
        <el-form-item label="区域名称">
          <el-input v-model="editForm.region_name" placeholder="请输入区域名称" maxlength="128" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="请输入群组描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加成员机构弹窗 -->
    <el-dialog v-model="addMemberDialogVisible" title="添加成员机构" width="500px" :close-on-click-modal="false">
      <el-form ref="addMemberFormRef" :model="addMemberForm" :rules="addMemberRules" label-width="80px">
        <el-form-item label="机构" prop="agency_id">
          <el-select v-model="addMemberForm.agency_id" placeholder="请选择成员机构" style="width: 100%" filterable>
            <el-option
              v-for="a in availableAgencies"
              :key="a.id"
              :label="a.agency_name"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addMemberForm.remark" placeholder="备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addMemberDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addMemberLoading" @click="handleAddMember">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 添加用户弹窗 -->
    <el-dialog v-model="addUserDialogVisible" title="添加群组用户" width="500px" :close-on-click-modal="false">
      <el-form ref="addUserFormRef" :model="addUserForm" :rules="addUserRules" label-width="80px">
        <el-form-item label="用户" prop="user_id">
          <el-select v-model="addUserForm.user_id" placeholder="请选择用户" style="width: 100%" filterable>
            <el-option
              v-for="u in availableUsers"
              :key="u.id"
              :label="`${u.real_name || u.username} (${u.agency_name || ''})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role_code">
          <el-select v-model="addUserForm.role_code" style="width: 100%">
            <el-option label="业务用户" value="user" />
            <el-option label="群组管理员" value="admin" />
            <el-option label="治理员" value="governor" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addUserDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="addUserLoading" @click="handleAddUser">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 修改用户角色弹窗 -->
    <el-dialog v-model="changeRoleDialogVisible" title="修改用户角色" width="450px" :close-on-click-modal="false">
      <el-form ref="changeRoleFormRef" :model="changeRoleForm" :rules="changeRoleRules" label-width="80px">
        <el-form-item label="用户">
          <span>{{ changeRoleTarget?.real_name || changeRoleTarget?.username }}</span>
        </el-form-item>
        <el-form-item label="新角色" prop="role_code">
          <el-select v-model="changeRoleForm.role_code" style="width: 100%">
            <el-option label="业务用户" value="user" />
            <el-option label="群组管理员" value="admin" />
            <el-option label="治理员" value="governor" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeRoleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="changeRoleLoading" @click="handleChangeRole">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 授权节点弹窗 -->
    <el-dialog v-model="addNodeDialogVisible" title="授权节点" width="600px" :close-on-click-modal="false">
      <el-table :data="availableNodeList" v-loading="availableNodesLoading" border stripe max-height="400">
        <el-table-column prop="node_code" label="节点编码" width="160" />
        <el-table-column prop="node_name" label="节点名称" min-width="160" />
        <el-table-column prop="agency_name" label="所属机构" min-width="140" />
        <el-table-column prop="node_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ nodeTypeLabel(row.node_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleAddNode(row)">
              授权
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-nodes-hint">
            暂无可授权节点，请先在基础资源管理中登记成员机构节点，或确认该节点尚未授权给本群组
          </div>
        </template>
      </el-table>
    </el-dialog>

    <!-- 授权数据集弹窗 -->
    <el-dialog v-model="addDatasetDialogVisible" title="授权数据集" width="600px" :close-on-click-modal="false">
      <el-table :data="availableDatasets" v-loading="availableDatasetsLoading" border stripe max-height="400">
        <el-table-column prop="dataset_name" label="数据集名称" min-width="180" />
        <el-table-column prop="dataset_code" label="数据集编码" width="160" />
        <el-table-column prop="agency_name" label="所属机构" min-width="140" />
        <el-table-column label="数据类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.data_type || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleAddDataset(row)">授权</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-nodes-hint">暂无可授权数据集，请先在数据资源管理中登记成员机构数据集</div>
        </template>
      </el-table>
    </el-dialog>

    <!-- 授权模板弹窗 -->
    <el-dialog v-model="addTemplateDialogVisible" title="授权模板" width="600px" :close-on-click-modal="false">
      <el-table :data="availableTemplates" v-loading="availableTemplatesLoading" border stripe max-height="400">
        <el-table-column prop="template_name" label="模板名称" min-width="180" />
        <el-table-column prop="template_code" label="模板编码" width="160" />
        <el-table-column prop="agency_name" label="所属机构" min-width="140" />
        <el-table-column label="适用场景" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.scenario || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleAddTemplate(row)">授权</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-nodes-hint">暂无可授权模板，请先在数据资源管理中登记任务模板</div>
        </template>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getGroupDetail, updateGroup,
  getGroupMembers, addGroupMember, removeGroupMember,
  getGroupUsers, addGroupUser, updateGroupUserRole, removeGroupUser,
  getGroupNodes, getAvailableGroupNodes, addGroupNode, removeGroupNode,
  getGroupDatasets, getAvailableGroupDatasets, addGroupDataset, removeGroupDataset,
  getGroupTemplates, getAvailableGroupTemplates, addGroupTemplate, removeGroupTemplate,
  getGroupLifecycleLogs,
  type GroupDetail, type GroupMemberItem, type GroupUserItem,
  type GroupNodeItem, type AvailableNodeItem, type LifecycleLogItem,
} from '@/api/group'
import { getAgencyList } from '@/api/agency'
import { getUserList } from '@/api/user'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const groupId = Number(route.params.id)

// ============================================================
// 通用响应解包
// ============================================================

function unwrapResponse<T = any>(raw: any): T {
  const maybeAxiosData = raw && typeof raw === 'object' && 'status' in raw && 'data' in raw
    ? raw.data
    : raw
  if (maybeAxiosData && typeof maybeAxiosData === 'object' && 'code' in maybeAxiosData && 'data' in maybeAxiosData) {
    return maybeAxiosData.data as T
  }
  return maybeAxiosData as T
}

function unwrapList<T = any>(raw: any): { items: T[]; total: number } {
  const data: any = unwrapResponse(raw)
  if (data?.items && Array.isArray(data.items)) {
    return { items: data.items, total: Number(data.total || 0) }
  }
  if (Array.isArray(data)) return { items: data, total: data.length }
  return { items: [], total: 0 }
}

function isSuccessResponse(raw: any): boolean {
  const m = raw && typeof raw === 'object' && 'status' in raw && 'data' in raw ? raw.data : raw
  if (m && typeof m === 'object' && 'code' in m) return m.code === 0
  return true
}

function getErrorMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

/** 当前有效成员机构状态。后端会保留 removed 等软删除记录，前端只展示 active。 */
function isActiveJoinStatus(status?: string | null) {
  return status === 'active'
}

// ============================================================
// 基础状态
// ============================================================

const pageLoading = ref(true)
const groupDetail = ref<GroupDetail | null>(null)
const activeTab = ref('members')

const memberList = ref<GroupMemberItem[]>([])
const userList = ref<GroupUserItem[]>([])
const nodeList = ref<GroupNodeItem[]>([])
const datasetList = ref<any[]>([])
const templateList = ref<any[]>([])
const lifecycleList = ref<LifecycleLogItem[]>([])

const membersLoading = ref(false)
const usersLoading = ref(false)
const nodesLoading = ref(false)
const datasetsLoading = ref(false)
const templatesLoading = ref(false)
const lifecycleLoading = ref(false)

const loadedTabs = ref<Set<string>>(new Set())

// ============================================================
// 权限
// ============================================================

const canEdit = computed(() => {
  if (!groupDetail.value) return false
  if (['archived', 'rejected', 'dissolved'].includes(groupDetail.value.status)) return false
  return authStore.hasPermission ? authStore.hasPermission('group:update') : true
})

const canManage = computed(() => {
  if (!groupDetail.value) return false
  if (['archived', 'rejected', 'dissolved'].includes(groupDetail.value.status)) return false
  return authStore.hasPermission ? (authStore.hasPermission('group:manage') || authStore.hasPermission('group:update')) : true
})

const canManageNodes = computed(() => {
  if (!groupDetail.value) return false
  if (['archived', 'rejected', 'dissolved'].includes(groupDetail.value.status)) return false
  if (authStore.isPlatformAdmin) return true
  return authStore.hasRole ? authStore.hasRole('admin', 'agency') : false
})

// ============================================================
// 统计卡片
// ============================================================

const statCards = computed(() => {
  if (!groupDetail.value) return []
  const s = groupDetail.value.summary
  return [
    { label: '成员机构', value: s.member_count || 0 },
    { label: '群组用户', value: s.user_count || 0 },
    { label: '授权节点', value: s.node_count || 0 },
    { label: '授权数据', value: datasetList.value.length },
    { label: '授权模板', value: templateList.value.length },
  ]
})

// ============================================================
// 数据加载
// ============================================================

async function loadDetail() {
  pageLoading.value = true
  try {
    const raw = await getGroupDetail(groupId)
    groupDetail.value = unwrapResponse<GroupDetail>(raw)
  } catch (err: any) {
    console.error('[GroupDetail] 加载群组详情失败:', err)
    ElMessage.error(getErrorMessage(err, '加载群组详情失败'))
    if (err?.response?.status === 404) router.replace('/groups')
  } finally {
    pageLoading.value = false
  }
}

async function loadMembers() {
  if (loadedTabs.value.has('members')) return
  membersLoading.value = true
  try {
    const raw = await getGroupMembers(groupId)
    const list = unwrapResponse<GroupMemberItem[]>(raw) || []
    memberList.value = list.filter(item => isActiveJoinStatus(item.join_status))
    loadedTabs.value.add('members')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载成员机构失败'))
  } finally {
    membersLoading.value = false
  }
}

async function loadUsers() {
  if (loadedTabs.value.has('users')) return
  usersLoading.value = true
  try {
    const raw = await getGroupUsers(groupId)
    userList.value = unwrapResponse<GroupUserItem[]>(raw) || []
    loadedTabs.value.add('users')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载群组用户失败'))
  } finally {
    usersLoading.value = false
  }
}

async function loadNodes() {
  if (loadedTabs.value.has('nodes')) return
  nodesLoading.value = true
  try {
    const raw = await getGroupNodes(groupId)
    nodeList.value = unwrapResponse<GroupNodeItem[]>(raw) || []
    loadedTabs.value.add('nodes')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载群组节点失败'))
  } finally {
    nodesLoading.value = false
  }
}

async function loadLifecycle() {
  if (loadedTabs.value.has('lifecycle')) return
  lifecycleLoading.value = true
  try {
    const raw = await getGroupLifecycleLogs(groupId, { page: 1, page_size: 50 })
    lifecycleList.value = unwrapList<LifecycleLogItem>(raw).items
    loadedTabs.value.add('lifecycle')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载生命周期日志失败'))
  } finally {
    lifecycleLoading.value = false
  }
}

async function loadDatasets() {
  if (loadedTabs.value.has('datasets')) return
  datasetsLoading.value = true
  try {
    const raw = await getGroupDatasets(groupId)
    datasetList.value = unwrapList(raw).items || []
    loadedTabs.value.add('datasets')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载群数据失败'))
  } finally {
    datasetsLoading.value = false
  }
}

async function loadTemplates() {
  if (loadedTabs.value.has('templates')) return
  templatesLoading.value = true
  try {
    const raw = await getGroupTemplates(groupId)
    templateList.value = unwrapList(raw).items || []
    loadedTabs.value.add('templates')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载群模板失败'))
  } finally {
    templatesLoading.value = false
  }
}

function handleTabChange(tabName: string | number) {
  const tab = String(tabName)
  if (tab === 'members') loadMembers()
  else if (tab === 'users') loadUsers()
  else if (tab === 'nodes') loadNodes()
  else if (tab === 'datasets') loadDatasets()
  else if (tab === 'templates') loadTemplates()
  else if (tab === 'lifecycle') loadLifecycle()
}

async function reloadTab(tab: string) {
  loadedTabs.value.delete(tab)
  if (tab === 'members') { memberList.value = []; await loadMembers() }
  else if (tab === 'users') { userList.value = []; await loadUsers() }
  else if (tab === 'nodes') { nodeList.value = []; await loadNodes() }
  else if (tab === 'datasets') { datasetList.value = []; await loadDatasets() }
  else if (tab === 'templates') { templateList.value = []; await loadTemplates() }
  else if (tab === 'lifecycle') { lifecycleList.value = []; await loadLifecycle() }
}

// ============================================================
// 编辑群组
// ============================================================

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editFormRef = ref<FormInstance>()
const editForm = reactive({ group_name: '', group_level: 'city', region_code: '', region_name: '', description: '' })
const editRules: FormRules = { group_name: [{ required: true, message: '请输入群组名称', trigger: 'blur' }] }

function showEditDialog() {
  if (!groupDetail.value) return
  editForm.group_name = groupDetail.value.group_name
  editForm.group_level = groupDetail.value.group_level
  editForm.region_code = groupDetail.value.region_code || ''
  editForm.region_name = groupDetail.value.region_name || ''
  editForm.description = groupDetail.value.description || ''
  editDialogVisible.value = true
}

async function handleEdit() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    editLoading.value = true
    try {
      const payload: any = { group_name: editForm.group_name }
      if (editForm.group_level) payload.group_level = editForm.group_level
      if (editForm.region_code) payload.region_code = editForm.region_code
      if (editForm.region_name) payload.region_name = editForm.region_name
      if (editForm.description) payload.description = editForm.description

      await updateGroup(groupId, payload)
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      await loadDetail()
    } catch (err: any) {
      ElMessage.error(getErrorMessage(err, '更新失败'))
    } finally {
      editLoading.value = false
    }
  })
}

// ============================================================
// 添加成员机构
// ============================================================

const addMemberDialogVisible = ref(false)
const addMemberLoading = ref(false)
const addMemberFormRef = ref<FormInstance>()
const addMemberForm = reactive({ agency_id: undefined as number | undefined, remark: '' })
const addMemberRules: FormRules = { agency_id: [{ required: true, message: '请选择机构', trigger: 'change' }] }
const availableAgencies = ref<any[]>([])

async function showAddMemberDialog() {
  addMemberForm.agency_id = undefined
  addMemberForm.remark = ''

  // 打开弹窗前刷新一次成员机构，避免刚移除成员后仍按旧 memberList 过滤下拉框。
  try {
    loadedTabs.value.delete('members')
    await loadMembers()
  } catch {}

  try {
    const raw = await getAgencyList({ page: 1, page_size: 100 })
    const data = unwrapList<any>(raw)
    // 只排除当前 active 成员；removed 等历史记录不应影响重新添加。
    const activeMemberIds = new Set(
      memberList.value
        .filter(m => isActiveJoinStatus(m.join_status))
        .map(m => m.agency_id)
    )
    availableAgencies.value = (data.items || []).filter((a: any) =>
      !activeMemberIds.has(a.id) && (a.status ? a.status === 'active' : true)
    )
  } catch (err) {
    availableAgencies.value = []
  }
  addMemberDialogVisible.value = true
}

async function handleAddMember() {
  if (!addMemberFormRef.value) return
  await addMemberFormRef.value.validate(async (valid) => {
    if (!valid) return
    addMemberLoading.value = true
    try {
      await addGroupMember(groupId, {
        agency_id: addMemberForm.agency_id!,
        member_type: 'participant',
        remark: addMemberForm.remark,
      })
      ElMessage.success('成员机构添加成功')
      addMemberDialogVisible.value = false
      await reloadTab('members')
      await loadDetail()
    } catch (err: any) {
      ElMessage.error(getErrorMessage(err, '添加失败'))
    } finally {
      addMemberLoading.value = false
    }
  })
}

async function handleRemoveMember(row: GroupMemberItem) {
  try {
    await ElMessageBox.confirm(`确认移除机构「${row.agency_name}」？`, '确认', {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await removeGroupMember(groupId, row.agency_id)
    ElMessage.success('已移除')
    await reloadTab('members')
    await loadDetail()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(getErrorMessage(err, '移除失败'))
  }
}

// ============================================================
// 添加群组用户
// ============================================================

const addUserDialogVisible = ref(false)
const addUserLoading = ref(false)
const addUserFormRef = ref<FormInstance>()
const addUserForm = reactive({ user_id: undefined as number | undefined, role_code: 'user' })
const addUserRules: FormRules = {
  user_id: [{ required: true, message: '请选择用户', trigger: 'change' }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
}
const availableUsers = ref<any[]>([])

async function showAddUserDialog() {
  addUserForm.user_id = undefined
  addUserForm.role_code = 'user'
  try {
    const raw = await getUserList({ page: 1, page_size: 100 })
    const data = unwrapList<any>(raw)
    const existingIds = new Set(userList.value.map(u => u.user_id))
    availableUsers.value = (data.items || []).filter((u: any) => !existingIds.has(u.id) && u.status === 'active')
  } catch (err) {
    availableUsers.value = []
  }
  addUserDialogVisible.value = true
}

async function handleAddUser() {
  if (!addUserFormRef.value) return
  await addUserFormRef.value.validate(async (valid) => {
    if (!valid) return
    addUserLoading.value = true
    try {
      await addGroupUser(groupId, {
        user_id: addUserForm.user_id!,
        role_code: addUserForm.role_code,
      })
      ElMessage.success('用户添加成功')
      addUserDialogVisible.value = false
      await reloadTab('users')
      await loadDetail()
    } catch (err: any) {
      ElMessage.error(getErrorMessage(err, '添加失败'))
    } finally {
      addUserLoading.value = false
    }
  })
}

// ============================================================
// 修改用户角色
// ============================================================

const changeRoleDialogVisible = ref(false)
const changeRoleLoading = ref(false)
const changeRoleFormRef = ref<FormInstance>()
const changeRoleTarget = ref<GroupUserItem | null>(null)
const changeRoleForm = reactive({ role_code: '' })
const changeRoleRules: FormRules = { role_code: [{ required: true, message: '请选择角色', trigger: 'change' }] }

function showChangeRoleDialog(row: GroupUserItem) {
  changeRoleTarget.value = row
  const currentRole = row.roles.find(r => r.scope_type === 'group')
  changeRoleForm.role_code = currentRole?.role_code || 'user'
  changeRoleDialogVisible.value = true
}

async function handleChangeRole() {
  if (!changeRoleFormRef.value || !changeRoleTarget.value) return
  await changeRoleFormRef.value.validate(async (valid) => {
    if (!valid) return
    changeRoleLoading.value = true
    try {
      await updateGroupUserRole(groupId, changeRoleTarget.value!.user_id, { role_code: changeRoleForm.role_code })
      ElMessage.success('角色修改成功')
      changeRoleDialogVisible.value = false
      await reloadTab('users')
      await loadDetail()
    } catch (err: any) {
      ElMessage.error(getErrorMessage(err, '修改失败'))
    } finally {
      changeRoleLoading.value = false
    }
  })
}

// ============================================================
// 移出用户
// ============================================================

async function handleRemoveUser(row: GroupUserItem) {
  try {
    await ElMessageBox.confirm(`确认将用户「${row.real_name || row.username}」移出群组？`, '确认', {
      confirmButtonText: '移出',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await removeGroupUser(groupId, row.user_id)
    ElMessage.success('已移出')
    await reloadTab('users')
    await loadDetail()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(getErrorMessage(err, '移出失败'))
  }
}

// ============================================================
// 授权节点
// ============================================================

const addNodeDialogVisible = ref(false)
const availableNodeList = ref<AvailableNodeItem[]>([])
const availableNodesLoading = ref(false)

async function showAddNodeDialog() {
  availableNodeList.value = []
  addNodeDialogVisible.value = true
  availableNodesLoading.value = true
  try {
    const raw = await getAvailableGroupNodes(groupId)
    availableNodeList.value = unwrapResponse<AvailableNodeItem[]>(raw) || []
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载可授权节点失败'))
  } finally {
    availableNodesLoading.value = false
  }
}

async function handleAddNode(row: AvailableNodeItem) {
  try {
    await addGroupNode(groupId, { node_id: row.node_id })
    ElMessage.success('节点授权成功')
    // 刷新可授权列表
    availableNodesLoading.value = true
    try {
      const raw = await getAvailableGroupNodes(groupId)
      availableNodeList.value = unwrapResponse<AvailableNodeItem[]>(raw) || []
    } catch {}
    availableNodesLoading.value = false
    // 刷新已授权列表和详情
    await reloadTab('nodes')
    await loadDetail()
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '授权失败'))
  }
}

async function handleRemoveNode(row: GroupNodeItem) {
  try {
    await ElMessageBox.confirm(`确认取消节点「${row.node_name}」的授权？`, '确认', {
      confirmButtonText: '取消授权',
      cancelButtonText: '返回',
      type: 'warning',
    })
    await removeGroupNode(groupId, row.node_id)
    ElMessage.success('节点授权已取消')
    await reloadTab('nodes')
    await loadDetail()
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(getErrorMessage(err, '取消授权失败'))
  }
}

// ============================================================
// 群数据授权
// ============================================================

const addDatasetDialogVisible = ref(false)
const availableDatasets = ref<any[]>([])
const availableDatasetsLoading = ref(false)

async function showAddDatasetDialog() {
  addDatasetDialogVisible.value = true
  availableDatasetsLoading.value = true
  try {
    const raw = await getAvailableGroupDatasets(groupId)
    availableDatasets.value = unwrapList(raw).items || []
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载可授权数据集失败'))
  } finally {
    availableDatasetsLoading.value = false
  }
}

async function handleAddDataset(row: any) {
  try {
    await addGroupDataset(groupId, row.id)
    ElMessage.success('数据集授权成功')
    addDatasetDialogVisible.value = false
    await reloadTab('datasets')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '授权失败'))
  }
}

async function handleRemoveDataset(row: any) {
  try {
    await ElMessageBox.confirm(`确认取消数据集「${row.dataset_name}」的授权？`, '确认', {
      confirmButtonText: '取消授权',
      cancelButtonText: '返回',
      type: 'warning',
    })
    await removeGroupDataset(groupId, row.dataset_id)
    ElMessage.success('数据集授权已取消')
    await reloadTab('datasets')
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(getErrorMessage(err, '取消授权失败'))
  }
}

// ============================================================
// 群模板授权
// ============================================================

const addTemplateDialogVisible = ref(false)
const availableTemplates = ref<any[]>([])
const availableTemplatesLoading = ref(false)

async function showAddTemplateDialog() {
  addTemplateDialogVisible.value = true
  availableTemplatesLoading.value = true
  try {
    const raw = await getAvailableGroupTemplates(groupId)
    availableTemplates.value = unwrapList(raw).items || []
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '加载可授权模板失败'))
  } finally {
    availableTemplatesLoading.value = false
  }
}

async function handleAddTemplate(row: any) {
  try {
    await addGroupTemplate(groupId, row.id)
    ElMessage.success('模板授权成功')
    addTemplateDialogVisible.value = false
    await reloadTab('templates')
  } catch (err: any) {
    ElMessage.error(getErrorMessage(err, '授权失败'))
  }
}

async function handleRemoveTemplate(row: any) {
  try {
    await ElMessageBox.confirm(`确认取消模板「${row.template_name}」的授权？`, '确认', {
      confirmButtonText: '取消授权',
      cancelButtonText: '返回',
      type: 'warning',
    })
    await removeGroupTemplate(groupId, row.template_id)
    ElMessage.success('模板授权已取消')
    await reloadTab('templates')
  } catch (err: any) {
    if (err !== 'cancel') ElMessage.error(getErrorMessage(err, '取消授权失败'))
  }
}

// ============================================================
// 导航
// ============================================================

function goBack() {
  router.push('/groups')
}

function goToTaskManagement() {
  router.push({ path: '/tasks', query: { group_id: groupId } })
}

// ============================================================
// 标签辅助
// ============================================================

const statusMap: Record<string, { label: string; type: string }> = {
  draft: { label: '草稿', type: 'info' },
  pending_approval: { label: '待审批', type: 'warning' },
  active: { label: '已启用', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  suspended: { label: '已暂停', type: 'danger' },
  dissolving: { label: '解散中', type: 'danger' },
  dissolved: { label: '已解散', type: 'info' },
  archived: { label: '已归档', type: 'info' },
  disabled: { label: '已禁用', type: 'danger' },
}

function statusLabel(s: string) { return statusMap[s]?.label || s }
function statusTagType(s: string) { return (statusMap[s]?.type || 'info') as any }

function approvalStatusLabel(s: string) {
  const map: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
  return map[s] || s
}
function approvalStatusType(s: string) {
  const map: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[s] || 'info'
}

function memberRoleLabel(r: string) {
  const map: Record<string, string> = { lead_agency: '牵头机构', participant: '参与机构', data_provider: '数据提供方', compute_provider: '计算提供方', observer: '观察者' }
  return map[r] || r
}

function groupRoleLabel(r: string) {
  const map: Record<string, string> = { admin: '群组管理员', user: '业务用户', governor: '治理员' }
  return map[r] || r
}

function nodeTypeLabel(t: string) {
  const map: Record<string, string> = {
    service_node: '服务节点', data_node: '数据节点', compute_node: '计算节点',
    blockchain_node: '区块链节点', gateway_node: '网关节点',
  }
  return map[t] || t
}

function eventTypeLabel(t: string) {
  const map: Record<string, string> = {
    group_created: '群组创建', group_updated: '群组更新', group_approved: '审批通过',
    group_rejected: '审批驳回', member_added: '添加成员', member_removed: '移除成员',
    user_added: '用户加入', user_removed: '用户移出', user_role_updated: '角色修改',
    node_authorized: '节点授权', node_revoked: '节点取消授权',
  }
  return map[t] || t
}

function joinStatusLabel(s: string) {
  const map: Record<string, string> = { active: '已加入', pending: '待确认', removed: '已移除', disabled: '已禁用' }
  return map[s] || s
}

function joinStatusType(s: string): any {
  const map: Record<string, string> = { active: 'success', pending: 'warning', removed: 'danger', disabled: 'danger' }
  return map[s] || 'info'
}

function authStatusLabel(s: string) {
  const map: Record<string, string> = { active: '已授权', disabled: '已禁用', revoked: '已撤销' }
  return map[s] || s
}

function authStatusType(s: string): any {
  const map: Record<string, string> = { active: 'success', disabled: 'danger', revoked: 'warning' }
  return map[s] || 'info'
}

function roleTagType(r: string): any {
  const map: Record<string, string> = { admin: 'danger', user: '', governor: 'warning' }
  return map[r] || 'info'
}

// ============================================================
// 初始化
// ============================================================

onMounted(async () => {
  await loadDetail()
  await loadMembers()
})
</script>

<style scoped>
.group-detail-page { padding: 20px; }
.info-card { margin-bottom: 20px; }
.card-header { 
  display: flex; 
  align-items: center; 
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.back-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
}
.back-icon {
  margin-right: 4px;
  font-weight: 600;
}
.card-title { font-size: 18px; font-weight: 600; color: #303133; }
.stat-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #409eff; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.tab-card { margin-bottom: 20px; }
.tab-toolbar { margin-bottom: 12px; }
.readonly-hint { font-size: 13px; color: #909399; }
.role-tag { margin-right: 4px; }
.empty-nodes-hint { padding: 40px 20px; text-align: center; color: #909399; font-size: 14px; }
</style>
