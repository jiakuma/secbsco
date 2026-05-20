<template>
  <div class="group-list-page">
    <!-- 权限范围提示卡片 -->
    <div class="permission-card">
      <div class="permission-content">
        <div class="permission-icon">
          <span v-if="authStore.isPlatformAdmin">🌐</span>
          <span v-else-if="isAgencyAdmin">🏢</span>
          <span v-else>👤</span>
        </div>
        <div class="permission-text">
          <div class="permission-title">当前可见范围</div>
          <div class="permission-desc">{{ permissionScopeText }}</div>
        </div>
      </div>
      <el-button v-if="canCreate" type="primary" @click="showCreateDialog">
        新建群组
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-value">{{ summaryData.totalCount }}</div>
        <div class="stat-label">可见群组数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ summaryData.activeCount }}</div>
        <div class="stat-label">活跃群组数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ summaryData.pendingCount }}</div>
        <div class="stat-label">待审批群组数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ summaryData.nodeCount }}</div>
        <div class="stat-label">已授权节点数</div>
      </div>
    </div>

    <!-- 分类 Tab -->
    <div class="category-tabs">
      <div
        v-for="tab in visibleTabs"
        :key="tab.value"
        :class="['tab-item', { active: searchForm.category === tab.value }]"
        @click="handleTabChange(tab.value)"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="tab-count">({{ tab.count }})</span>
      </div>
    </div>

    <!-- 查询区域 -->
    <div class="search-bar">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="群组编码 / 名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="群组状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="待审批" value="pending_approval" />
            <el-option label="活跃" value="active" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="解散中" value="dissolving" />
            <el-option label="已解散" value="dissolved" />
            <el-option label="已归档" value="archived" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批状态">
          <el-select
            v-model="searchForm.approval_status"
            placeholder="全部"
            clearable
            style="width: 120px"
          >
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="牵头机构">
          <el-select
            v-model="searchForm.lead_agency_id"
            placeholder="全部机构"
            clearable
            filterable
            style="width: 200px"
          >
            <el-option
              v-for="agency in agencyList"
              :key="agency.id"
              :label="agency.agency_name"
              :value="agency.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 群组列表表格 -->
    <el-table
      :data="groupList"
      v-loading="loading"
      border
      stripe
      style="width: 100%"
      :empty-text="emptyText"
    >
      <el-table-column label="群组名称" min-width="220">
        <template #default="{ row }">
          <div class="group-name-cell">
            <div class="group-name">{{ row.group_name }}</div>
            <div class="group-meta">
              <span class="group-code">{{ row.group_code }}</span>
              <span v-if="row.my_relation" class="group-relation">{{ relationLabel(row.my_relation) }}</span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="region_name" label="行政区划" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.region_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="lead_agency_name" label="牵头机构" min-width="140" show-overflow-tooltip />
      <el-table-column prop="member_count" label="成员机构数" width="100" align="center" />
      <el-table-column prop="user_count" label="群组用户数" width="100" align="center" />
      <el-table-column prop="node_count" label="授权节点数" width="100" align="center" />
      <el-table-column label="任务数" width="80" align="center">
        <template #default="{ row }">
          <span class="task-count">{{ row.task_count || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="群组状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="approval_status" label="审批状态" width="100">
        <template #default="{ row }">
          <el-tag
            :type="approvalDisplayType(row)"
            size="small"
          >
            {{ approvalDisplayLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="goDetail(row.id)">
            详情
          </el-button>
          <el-button
            v-if="row.can_manage && row.status === 'active'"
            type="primary"
            link
            size="small"
            @click="goManage(row.id)"
          >
            管理
          </el-button>
          <template v-if="row.status === 'pending_approval' && row.can_approve">
            <el-button type="success" link size="small" @click="handleApprove(row)">
              审批
            </el-button>
            <el-button type="danger" link size="small" @click="handleReject(row)">
              驳回
            </el-button>
          </template>
          <template v-if="row.status === 'dissolving' && row.can_approve_delete">
            <el-button type="success" link size="small" @click="handleApproveDelete(row)">
              通过删除
            </el-button>
            <el-button type="danger" link size="small" @click="handleRejectDelete(row)">
              驳回删除
            </el-button>
          </template>
          <el-button
            v-if="row.can_delete && row.status !== 'dissolving'"
            type="danger"
            link
            size="small"
            @click="handleDelete(row)"
          >
            {{ row.need_delete_approval ? '申请删除' : '删除' }}
          </el-button>
          <el-tag v-if="row.status === 'dissolving'" type="warning" size="small" style="margin-left: 8px">
            删除审批中
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态提示 -->
    <div v-if="!loading && groupList.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <div class="empty-title">暂无可见群组</div>
      <div class="empty-desc">{{ emptyDescText }}</div>
      <el-button v-if="canCreate" type="primary" @click="showCreateDialog">
        新建群组
      </el-button>
    </div>

    <!-- 分页 -->
    <div v-if="groupList.length > 0" class="pagination-bar">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchList"
        @current-change="fetchList"
      />
    </div>

    <!-- 创建群组弹窗 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建群组"
      width="650px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="100px"
      >
        <el-form-item label="群组编码" prop="group_code">
          <el-input v-model="createForm.group_code" placeholder="请输入群组编码" maxlength="64" />
        </el-form-item>
        <el-form-item label="群组名称" prop="group_name">
          <el-input v-model="createForm.group_name" placeholder="请输入群组名称" maxlength="128" />
        </el-form-item>
        <el-form-item label="群组层级" prop="group_level">
          <el-select v-model="createForm.group_level" style="width: 100%">
            <el-option label="县级" value="county" />
            <el-option label="市级" value="city" />
            <el-option label="省级" value="province" />
            <el-option label="国家级" value="national" />
          </el-select>
        </el-form-item>
        <el-form-item label="牵头机构" prop="lead_agency_id">
          <el-select
            v-model="createForm.lead_agency_id"
            placeholder="请选择牵头机构"
            style="width: 100%"
            @change="handleLeadAgencyChange"
          >
            <el-option
              v-for="agency in agencyList"
              :key="agency.id"
              :label="`${agency.agency_name} (${agency.agency_code})`"
              :value="agency.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="成员机构" prop="member_agency_ids">
          <el-select
            v-model="createForm.member_agency_ids"
            multiple
            placeholder="请选择成员机构（可选，支持下级机构或同级协作机构）"
            style="width: 100%"
          >
            <el-option
              v-for="agency in memberAgencyCandidates"
              :key="agency.id"
              :label="`${agency.agency_name} (${agency.agency_code})`"
              :value="agency.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="区域编码">
          <el-input v-model="createForm.region_code" placeholder="请输入区域编码" maxlength="64" />
        </el-form-item>
        <el-form-item label="区域名称">
          <el-input v-model="createForm.region_name" placeholder="请输入区域名称" maxlength="128" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入群组描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 驳回弹窗 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="驳回群组申请"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-width="80px">
        <el-form-item label="驳回原因" prop="reason">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejectLoading" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 删除驳回弹窗 -->
    <el-dialog
      v-model="deleteRejectDialogVisible"
      title="驳回删除申请"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form ref="deleteRejectFormRef" :model="deleteRejectForm" :rules="deleteRejectRules" label-width="80px">
        <el-form-item label="驳回原因" prop="reason">
          <el-input v-model="deleteRejectForm.reason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteRejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="deleteRejectLoading" @click="confirmDeleteReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getGroupList, createGroup, approveGroup, rejectGroup,
  requestDeleteGroup, approveDeleteGroup, rejectDeleteGroup,
  type GroupItem,
} from '@/api/group'
import { getAgencyList } from '@/api/agency'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function unwrapResponse<T = any>(raw: any): T {
  const maybeAxiosData = raw && typeof raw === 'object' && 'status' in raw && 'data' in raw
    ? raw.data
    : raw

  if (
    maybeAxiosData &&
    typeof maybeAxiosData === 'object' &&
    'code' in maybeAxiosData &&
    'data' in maybeAxiosData
  ) {
    return maybeAxiosData.data as T
  }

  return maybeAxiosData as T
}

function unwrapList<T = any>(raw: any): { items: T[]; total: number; page?: number; page_size?: number; summary?: any } {
  const data: any = unwrapResponse(raw)

  if (data?.items && Array.isArray(data.items)) {
    return {
      items: data.items,
      total: Number(data.total || 0),
      page: data.page,
      page_size: data.page_size,
      summary: data.summary,
    }
  }

  if (Array.isArray(data)) {
    return { items: data, total: data.length }
  }

  return { items: [], total: 0 }
}

function isSuccessResponse(raw: any): boolean {
  const maybeAxiosData = raw && typeof raw === 'object' && 'status' in raw && 'data' in raw
    ? raw.data
    : raw

  if (maybeAxiosData && typeof maybeAxiosData === 'object' && 'code' in maybeAxiosData) {
    return maybeAxiosData.code === 0
  }
  return true
}

function getErrorMessage(error: any, fallback: string) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    fallback
  )
}

const searchForm = reactive({
  keyword: '',
  status: '',
  approval_status: '',
  lead_agency_id: undefined as number | undefined,
  category: 'all',
})
const pagination = reactive({ page: 1, page_size: 10, total: 0 })
const loading = ref(false)
const groupList = ref<GroupItem[]>([])
const agencyList = ref<any[]>([])
const backendSummary = ref<any>(null)

const memberAgencyCandidates = computed(() => {
  const leadId = createForm.lead_agency_id
  if (!leadId) return []

  const leadAgency = agencyList.value.find(a => a.id === leadId)
  if (!leadAgency) return []

  const leadAncestorIds = new Set<number>()
  let current = leadAgency
  while (current?.parent_agency_id) {
    leadAncestorIds.add(current.parent_agency_id)
    current = agencyList.value.find(a => a.id === current.parent_agency_id)
  }

  const result: any[] = []
  const addedIds = new Set<number>()

  function collectDescendants(parentId: number) {
    for (const agency of agencyList.value) {
      if (addedIds.has(agency.id)) continue
      if (agency.parent_agency_id === parentId) {
        addedIds.add(agency.id)
        if (agency.id !== leadId && !leadAncestorIds.has(agency.id)) {
          result.push(agency)
        }
        collectDescendants(agency.id)
      }
    }
  }

  collectDescendants(leadId)

  const parentId = leadAgency.parent_agency_id
  if (parentId) {
    for (const agency of agencyList.value) {
      if (
        agency.parent_agency_id === parentId &&
        agency.id !== leadId &&
        !addedIds.has(agency.id) &&
        !leadAncestorIds.has(agency.id)
      ) {
        addedIds.add(agency.id)
        result.push(agency)
      }
    }
  }

  return result
})

const isAgencyAdmin = computed(() => {
  return authStore.hasRole('admin', 'agency') && !authStore.isPlatformAdmin
})

const isBusinessUser = computed(() => {
  return !authStore.isPlatformAdmin && !isAgencyAdmin.value
})

const permissionScopeText = computed(() => {
  if (authStore.isPlatformAdmin) {
    return '全平台群组'
  }
  if (isAgencyAdmin.value) {
    return '本机构及下辖机构参与的群组，支持上级监管下级，平级机构和权限范围外机构群组默认不可见'
  }
  return '我加入的群组'
})

const emptyDescText = computed(() => {
  if (canCreate.value) {
    return '可能原因是当前机构尚未加入任何群组、下辖机构尚未创建或加入群组、当前权限范围内没有群组数据'
  }
  return '请联系机构管理员或平台管理员创建群组'
})

const emptyText = computed(() => {
  return '暂无数据'
})

const canCreate = computed(() => {
  const isGroupAdminOnly = authStore.hasRole('admin', 'group') &&
    !authStore.hasRole('admin', 'platform') &&
    !authStore.hasRole('admin', 'agency')
  if (isGroupAdminOnly) return false
  return authStore.hasPermission ? authStore.hasPermission('group:create') : true
})

const platformAdminTabs = [
  { label: '全部群组', value: 'all' },
  { label: '待审批', value: 'pending_approval' },
  { label: '活跃群组', value: 'active' },
  { label: '已归档', value: 'archived' },
]

const agencyAdminTabs = [
  { label: '全部群组', value: 'all' },
  { label: '我牵头的', value: 'my_lead' },
  { label: '我参与的', value: 'my_participate' },
  { label: '下级机构群组', value: 'subordinate' },
  { label: '待审批', value: 'pending_approval' },
]

const businessUserTabs = [
  { label: '我参与的群组', value: 'my_participate' },
]

const visibleTabs = computed(() => {
  if (authStore.isPlatformAdmin) {
    return platformAdminTabs.map(tab => ({
      ...tab,
      count: getTabCount(tab.value),
    }))
  }
  if (isAgencyAdmin.value) {
    return agencyAdminTabs.map(tab => ({
      ...tab,
      count: getTabCount(tab.value),
    }))
  }
  return businessUserTabs.map(tab => ({
    ...tab,
    count: getTabCount(tab.value),
  }))
})

function getTabCount(category: string): number | undefined {
  if (!backendSummary.value) return undefined
  return backendSummary.value[category + '_count']
}

const summaryData = computed(() => {
  if (backendSummary.value) {
    return {
      totalCount: backendSummary.value.total_count || 0,
      activeCount: backendSummary.value.active_count || 0,
      pendingCount: backendSummary.value.pending_count || 0,
      nodeCount: backendSummary.value.node_count || 0,
    }
  }

  const items = groupList.value
  return {
    totalCount: pagination.total,
    activeCount: items.filter(g => g.status === 'active').length,
    pendingCount: items.filter(g => g.status === 'pending_approval').length,
    nodeCount: items.reduce((sum, g) => sum + (g.node_count || 0), 0),
  }
})

function handleTabChange(category: string) {
  searchForm.category = category
  pagination.page = 1
  fetchList()
}

async function fetchList() {
  loading.value = true
  try {
    const params: any = {
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
      approval_status: searchForm.approval_status || undefined,
      lead_agency_id: searchForm.lead_agency_id || undefined,
      category: searchForm.category !== 'all' ? searchForm.category : undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    }

    const raw = await getGroupList(params)
    const data = unwrapList<GroupItem>(raw)
    groupList.value = (data.items || []).map(item => ({
      ...item,
      task_count: item.task_count ?? 0,
      my_relation: item.my_relation || '',
      can_manage: item.can_manage ?? false,
      can_approve: item.can_approve ?? false,
      can_delete: item.can_delete ?? false,
      need_delete_approval: item.need_delete_approval ?? false,
      can_approve_delete: item.can_approve_delete ?? false,
    }))
    pagination.total = data.total || 0
    if (data.summary) {
      backendSummary.value = data.summary
    }
  } catch (err: any) {
    console.error('[GroupList] 加载群组列表失败:', err)
    ElMessage.error(getErrorMessage(err, '加载群组列表失败'))
    groupList.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

async function fetchAgencyList() {
  try {
    const raw = await getAgencyList({ page: 1, page_size: 100 })
    const data = unwrapList<any>(raw)
    agencyList.value = data.items || []
  } catch (err) {
    console.warn('[GroupList] 加载机构列表失败:', err)
    agencyList.value = []
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.status = ''
  searchForm.approval_status = ''
  searchForm.lead_agency_id = undefined
  searchForm.category = 'all'
  pagination.page = 1
  fetchList()
}

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref<FormInstance>()

const createForm = reactive({
  group_code: '',
  group_name: '',
  group_level: 'city',
  region_code: '',
  region_name: '',
  lead_agency_id: undefined as number | undefined,
  member_agency_ids: [] as number[],
  description: '',
})

const createRules: FormRules = {
  group_code: [{ required: true, message: '请输入群组编码', trigger: 'blur' }],
  group_name: [{ required: true, message: '请输入群组名称', trigger: 'blur' }],
  lead_agency_id: [{ required: true, message: '请选择牵头机构', trigger: 'change' }],
}

async function showCreateDialog() {
  createForm.group_code = ''
  createForm.group_name = ''
  createForm.group_level = 'city'
  createForm.region_code = ''
  createForm.region_name = ''
  createForm.lead_agency_id = undefined
  createForm.member_agency_ids = []
  createForm.description = ''

  if (agencyList.value.length === 0) {
    await fetchAgencyList()
  }

  createDialogVisible.value = true
}

function handleLeadAgencyChange() {
  createForm.member_agency_ids = []
}

async function handleCreate() {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    createLoading.value = true
    try {
      const payload: any = {
        group_code: createForm.group_code,
        group_name: createForm.group_name,
        group_level: createForm.group_level,
        lead_agency_id: createForm.lead_agency_id,
      }

      if (createForm.member_agency_ids.length > 0) {
        payload.member_agency_ids = createForm.member_agency_ids
      }
      if (createForm.region_code) payload.region_code = createForm.region_code
      if (createForm.region_name) payload.region_name = createForm.region_name
      if (createForm.description) payload.description = createForm.description

      const raw = await createGroup(payload)

      if (isSuccessResponse(raw)) {
        const created = unwrapResponse<any>(raw)

        if (created?.status === 'pending_approval') {
          ElMessage.success('群组创建申请已提交，等待共同上级机构审批')
        } else {
          ElMessage.success('群组创建成功，已进入活跃状态')
        }

        createDialogVisible.value = false
        await fetchList()

        const newId = created?.id
        if (newId) {
          router.push(`/groups/${newId}`)
        }
      } else {
        ElMessage.error('创建失败')
      }
    } catch (err: any) {
      console.error('[GroupList] 创建失败:', err)
      ElMessage.error(getErrorMessage(err, '创建失败'))
    } finally {
      createLoading.value = false
    }
  })
}

async function handleApprove(row: GroupItem) {
  try {
    await ElMessageBox.confirm('确认审批通过该群组？', '审批确认', {
      confirmButtonText: '通过',
      cancelButtonText: '取消',
      type: 'info',
    })

    await approveGroup(row.id, { remark: '审批通过' })
    ElMessage.success('审批通过')
    await fetchList()
  } catch (err: any) {
    if (err !== 'cancel') {
      console.error('[GroupList] 审批失败:', err)
      ElMessage.error(getErrorMessage(err, '审批失败'))
    }
  }
}

const rejectDialogVisible = ref(false)
const rejectLoading = ref(false)
const rejectFormRef = ref<FormInstance>()
const rejectTargetId = ref<number>(0)

const rejectForm = reactive({ reason: '' })
const rejectRules: FormRules = {
  reason: [{ required: true, message: '请输入驳回原因', trigger: 'blur' }],
}

function handleReject(row: GroupItem) {
  rejectTargetId.value = row.id
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectFormRef.value) return

  await rejectFormRef.value.validate(async (valid) => {
    if (!valid) return

    rejectLoading.value = true
    try {
      await rejectGroup(rejectTargetId.value, { reason: rejectForm.reason })
      ElMessage.success('已驳回')
      rejectDialogVisible.value = false
      await fetchList()
    } catch (err: any) {
      console.error('[GroupList] 驳回失败:', err)
      ElMessage.error(getErrorMessage(err, '驳回失败'))
    } finally {
      rejectLoading.value = false
    }
  })
}

async function handleDelete(row: GroupItem) {
  const isDirectDelete = !row.need_delete_approval
  const confirmMsg = isDirectDelete
    ? `确认删除群组「${row.group_name}」？\n\n当前阶段将物理删除群组及其成员、用户、节点授权和生命周期日志数据，此操作不可恢复。`
    : `确认申请删除群组「${row.group_name}」？\n\n该群组为同级协作群组，删除申请将提交至共同上级机构审批。`

  try {
    await ElMessageBox.confirm(confirmMsg, isDirectDelete ? '删除确认' : '申请删除确认', {
      confirmButtonText: isDirectDelete ? '删除' : '提交申请',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const raw = await requestDeleteGroup(row.id)
    if (isSuccessResponse(raw)) {
      const result = unwrapResponse<any>(raw)
      if (result.deleted) {
        ElMessage.success('群组已删除')
      } else {
        ElMessage.success('删除申请已提交，等待审批')
      }
      await fetchList()
    }
  } catch (err: any) {
    if (err !== 'cancel') {
      console.error('[GroupList] 删除失败:', err)
      ElMessage.error(getErrorMessage(err, '删除失败'))
    }
  }
}

async function handleApproveDelete(row: GroupItem) {
  try {
    await ElMessageBox.confirm(
      `确认审批通过删除群组「${row.group_name}」？\n\n审批通过后将物理删除群组及其成员、用户、节点授权和生命周期日志数据，此操作不可恢复。`,
      '删除审批确认',
      {
        confirmButtonText: '通过删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await approveDeleteGroup(row.id)
    ElMessage.success('删除审批通过，群组已删除')
    await fetchList()
  } catch (err: any) {
    if (err !== 'cancel') {
      console.error('[GroupList] 删除审批失败:', err)
      ElMessage.error(getErrorMessage(err, '删除审批失败'))
    }
  }
}

const deleteRejectDialogVisible = ref(false)
const deleteRejectLoading = ref(false)
const deleteRejectFormRef = ref<FormInstance>()
const deleteRejectTargetId = ref<number>(0)
const deleteRejectForm = reactive({ reason: '' })
const deleteRejectRules: FormRules = {
  reason: [{ required: true, message: '请输入驳回原因', trigger: 'blur' }],
}

function handleRejectDelete(row: GroupItem) {
  deleteRejectTargetId.value = row.id
  deleteRejectForm.reason = ''
  deleteRejectDialogVisible.value = true
}

async function confirmDeleteReject() {
  if (!deleteRejectFormRef.value) return

  await deleteRejectFormRef.value.validate(async (valid) => {
    if (!valid) return

    deleteRejectLoading.value = true
    try {
      await rejectDeleteGroup(deleteRejectTargetId.value, { reason: deleteRejectForm.reason })
      ElMessage.success('删除申请已驳回')
      deleteRejectDialogVisible.value = false
      await fetchList()
    } catch (err: any) {
      console.error('[GroupList] 驳回删除失败:', err)
      ElMessage.error(getErrorMessage(err, '驳回删除失败'))
    } finally {
      deleteRejectLoading.value = false
    }
  })
}

function goDetail(id: number) {
  router.push(`/groups/${id}`)
}

function goManage(id: number) {
  router.push(`/groups/${id}?tab=members`)
}

const statusMap: Record<string, { label: string; type: string }> = {
  draft: { label: '草稿', type: 'info' },
  pending_approval: { label: '待审批', type: 'warning' },
  active: { label: '活跃', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  dissolving: { label: '解散中', type: 'danger' },
  dissolved: { label: '已解散', type: 'info' },
  archived: { label: '已归档', type: 'info' },
  disabled: { label: '已禁用', type: 'danger' },
}

function statusLabel(status: string) {
  return statusMap[status]?.label || status
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return (statusMap[status]?.type || 'info') as any
}

function approvalStatusLabel(status: string) {
  const map: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
  return map[status] || status
}

function approvalStatusType(status: string): any {
  const map: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

function approvalDisplayLabel(row: GroupItem): string {
  if (!row.approval_required) {
    return '无需审批'
  }
  const status = row.approval_status
  if (status === 'pending') return '待审批'
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '无需审批'
}

function approvalDisplayType(row: GroupItem): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (!row.approval_required) {
    return 'info'
  }
  const status = row.approval_status
  if (status === 'pending') return 'warning'
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function relationLabel(relation: string): string {
  const map: Record<string, string> = {
    lead_agency: '牵头机构',
    participant: '参与机构',
    subordinate: '下级机构群组',
    pending_approval: '待审批',
    observer: '观察者',
  }
  return map[relation] || relation
}

onMounted(() => {
  if (isBusinessUser.value) {
    searchForm.category = 'my_participate'
  }
  fetchList()
  fetchAgencyList()
})
</script>

<style scoped>
.group-list-page {
  padding: 20px;
  background: #f5f7fb;
  min-height: 100%;
}

.permission-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 12px;
  margin-bottom: 16px;
}

.permission-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.permission-icon {
  font-size: 28px;
}

.permission-title {
  font-size: 14px;
  font-weight: 600;
  color: #0369a1;
  margin-bottom: 2px;
}

.permission-desc {
  font-size: 13px;
  color: #0c4a6e;
  max-width: 500px;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
}

.category-tabs {
  display: flex;
  gap: 4px;
  background: #ffffff;
  padding: 8px;
  border-radius: 10px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
}

.tab-item {
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #64748b;
  transition: all 0.2s;
}

.tab-item:hover {
  background: #f1f5f9;
  color: #334155;
}

.tab-item.active {
  background: #2563eb;
  color: #ffffff;
}

.tab-count {
  font-size: 12px;
  margin-left: 4px;
}

.search-bar {
  margin-bottom: 16px;
  background: #ffffff;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.group-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.group-name {
  font-weight: 600;
  color: #111827;
}

.group-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.group-code {
  color: #6b7280;
}

.group-relation {
  color: #2563eb;
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.task-count {
  font-weight: 700;
  color: #2563eb;
  font-size: 15px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  margin-top: 16px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #6b7280;
  text-align: center;
  max-width: 400px;
  margin-bottom: 20px;
}

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  background: #ffffff;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

@media (max-width: 1024px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }

  .permission-card {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .category-tabs {
    flex-wrap: wrap;
  }
}
</style>
