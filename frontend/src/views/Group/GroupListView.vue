<template>
  <div class="group-list-page">
    <!-- 搜索栏 -->
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
        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="待审批" value="pending_approval" />
            <el-option label="已启用" value="active" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已暂停" value="suspended" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button v-if="canCreate" type="primary" @click="showCreateDialog">
        新建群组
      </el-button>
    </div>

    <!-- 群组列表表格 -->
    <el-table :data="groupList" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="group_code" label="群组编码" min-width="200" show-overflow-tooltip />
      <el-table-column prop="group_name" label="群组名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="lead_agency_name" label="牵头机构" min-width="140" show-overflow-tooltip />
      <el-table-column prop="status" label="群组状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="approval_status" label="审批状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.approval_status && row.approval_status !== 'none'"
                  :type="approvalStatusType(row.approval_status)" size="small">
            {{ approvalStatusLabel(row.approval_status) }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="member_count" label="成员" width="70" align="center" />
      <el-table-column prop="user_count" label="用户" width="60" align="center" />
      <el-table-column prop="node_count" label="节点" width="60" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="goDetail(row.id)">
            详情
          </el-button>
          <el-button
            v-if="row.status === 'pending_approval' && canApprove(row)"
            type="success"
            link
            size="small"
            @click="handleApprove(row)"
          >
            审批通过
          </el-button>
          <el-button
            v-if="row.status === 'pending_approval' && canApprove(row)"
            type="danger"
            link
            size="small"
            @click="handleReject(row)"
          >
            驳回
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-bar">
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
          <el-select v-model="createForm.lead_agency_id" placeholder="请选择牵头机构" style="width: 100%">
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
            placeholder="请选择成员机构（可选）"
            style="width: 100%"
          >
            <el-option
              v-for="agency in agencyList"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getGroupList, createGroup, approveGroup, rejectGroup,
  type GroupItem,
} from '@/api/group'
import { getAgencyList } from '@/api/agency'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// ============================================================
// 通用响应解包
// ============================================================

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

function unwrapList<T = any>(raw: any): { items: T[]; total: number; page?: number; page_size?: number } {
  const data: any = unwrapResponse(raw)

  if (data?.items && Array.isArray(data.items)) {
    return {
      items: data.items,
      total: Number(data.total || 0),
      page: data.page,
      page_size: data.page_size,
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

// ============================================================
// 搜索
// ============================================================

const searchForm = reactive({ keyword: '', status: '' })
const pagination = reactive({ page: 1, page_size: 10, total: 0 })
const loading = ref(false)
const groupList = ref<GroupItem[]>([])

// ============================================================
// 权限判断
// ============================================================

const canCreate = computed(() => {
  // group_admin 不能创建，只有 platform_admin 和 agency_admin 可以
  const isGroupAdminOnly = authStore.hasRole('admin', 'group') &&
    !authStore.hasRole('admin', 'platform') &&
    !authStore.hasRole('admin', 'agency')
  if (isGroupAdminOnly) return false
  return authStore.hasPermission ? authStore.hasPermission('group:create') : true
})

function canApprove(row: GroupItem): boolean {
  if (row.status !== 'pending_approval') return false
  // 平台管理员可以审批全部
  if (authStore.isPlatformAdmin) return true
  return false
}

// ============================================================
// 数据加载
// ============================================================

async function fetchList() {
  loading.value = true
  try {
    const raw = await getGroupList({
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    })

    const data = unwrapList<GroupItem>(raw)
    groupList.value = data.items || []
    pagination.total = data.total || 0
  } catch (err: any) {
    console.error('[GroupList] 加载群组列表失败:', err)
    ElMessage.error(getErrorMessage(err, '加载群组列表失败'))
    groupList.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.status = ''
  pagination.page = 1
  fetchList()
}

// ============================================================
// 创建群组
// ============================================================

const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref<FormInstance>()
const agencyList = ref<any[]>([])

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

  try {
    const raw = await getAgencyList({ page: 1, page_size: 100 })
    const data = unwrapList<any>(raw)
    agencyList.value = data.items || []
  } catch (err) {
    console.warn('[GroupList] 加载机构列表失败:', err)
    agencyList.value = []
  }

  createDialogVisible.value = true
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
          ElMessage.success('群组创建申请已提交，等待上级机构审批')
        } else {
          ElMessage.success('群组创建成功')
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
      const msg = getErrorMessage(err, '创建失败')
      // 显示详细错误信息
      if (msg.includes('机构管理员')) {
        ElMessage.error(msg)
      } else {
        ElMessage.error(msg)
      }
    } finally {
      createLoading.value = false
    }
  })
}

// ============================================================
// 审批通过
// ============================================================

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

// ============================================================
// 驳回
// ============================================================

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

// ============================================================
// 导航
// ============================================================

function goDetail(id: number) {
  router.push(`/groups/${id}`)
}

// ============================================================
// 状态标签
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

// ============================================================
// 初始化
// ============================================================

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.group-list-page {
  padding: 20px;
}
.search-bar {
  margin-bottom: 16px;
}
.action-bar {
  margin-bottom: 16px;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
