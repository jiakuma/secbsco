<template>
  <div class="user-manage-view">
    <div class="page-header">
      <div>
        <h2>用户管理</h2>
        <p>维护平台用户、所属机构与角色绑定关系，支持按用户状态和关键词快速检索。</p>
      </div>

      <el-button type="primary" @click="openCreateDialog">
        创建用户
      </el-button>
    </div>

    <el-row :gutter="12" class="summary-row">
      <el-col :xs="12" :sm="8" :md="6" :lg="4">
        <div class="summary-card">
          <div class="summary-value">{{ total }}</div>
          <div class="summary-label">用户总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4">
        <div class="summary-card">
          <div class="summary-value">{{ activeCount }}</div>
          <div class="summary-label">当前页正常</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6" :lg="4">
        <div class="summary-card">
          <div class="summary-value">{{ disabledCount }}</div>
          <div class="summary-label">当前页停用</div>
        </div>
      </el-col>
    </el-row>

    <el-card class="section-card" shadow="never">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="用户名 / 姓名 / 手机号 / 邮箱"
            clearable
            style="width: 260px"
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
            <el-option label="正常" value="active" />
            <el-option label="停用" value="disabled" />
            <el-option label="锁定" value="locked" />
            <el-option label="归档" value="archived" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="section-card">
      <el-table
        :data="userList"
        stripe
        border
        v-loading="loading"
        empty-text="暂无用户数据"
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" min-width="140" show-overflow-tooltip />
        <el-table-column prop="real_name" label="真实姓名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="agency_name" label="所属机构" min-width="190" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.agency_name || '-' }}</span>
            <span v-if="row.agency_id" class="muted-text">（ID: {{ row.agency_id }}）</span>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="130" show-overflow-tooltip />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />

        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="last_login_time" label="最后登录" min-width="165" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.last_login_time || row.last_login_at || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewRoles(row)">角色</el-button>
            <el-button
              v-if="row.status === 'active'"
              link
              type="danger"
              @click="handleDisable(row)"
            >
              停用
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <span class="total-text">Total {{ total }}</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next, jumper"
          @current-change="fetchUsers"
          @size-change="fetchUsers"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="showCreateDialog"
      title="创建用户"
      width="620px"
      destroy-on-close
    >
      <el-alert
        class="dialog-alert"
        type="info"
        show-icon
        :closable="false"
        title="用户创建后默认只是机构用户，是否成为机构管理员、群组管理员、业务用户或治理员，需要在角色授权中单独绑定。"
      />

      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="96px"
      >
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="createForm.username" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="初始密码" prop="password">
              <el-input
                v-model="createForm.password"
                type="password"
                placeholder="请输入密码"
                show-password
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="真实姓名" prop="real_name">
              <el-input v-model="createForm.real_name" placeholder="请输入真实姓名" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="所属机构" prop="agency_id">
              <el-select
                v-model="createForm.agency_id"
                filterable
                clearable
                placeholder="请选择所属机构"
                style="width: 100%"
                :loading="agencyLoading"
              >
                <el-option
                  v-for="agency in agencyList"
                  :key="agency.id"
                  :label="formatAgencyOption(agency)"
                  :value="agency.id"
                />
              </el-select>
              <div class="form-tip">
                不再手填机构 ID，避免出现 agency_id 不存在导致外键报错。
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="手机号">
              <el-input v-model="createForm.phone" placeholder="请输入手机号" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="createForm.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="showRolesDialog"
      title="用户角色"
      size="620px"
      destroy-on-close
    >
      <template v-if="currentUser">
        <div class="role-user-card">
          <div>
            <div class="role-user-name">{{ currentUser.real_name || currentUser.username }}</div>
            <div class="role-user-meta">
              {{ currentUser.username }} ｜ {{ currentUser.agency_name || '未绑定机构' }}
            </div>
          </div>
          <el-tag :type="statusTagType(currentUser.status)">
            {{ statusText(currentUser.status) }}
          </el-tag>
        </div>
      </template>

      <el-table :data="userRoles" stripe border size="small" empty-text="暂无角色绑定">
        <el-table-column prop="role_code" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role_code)">
              {{ roleText(row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="scope_type" label="作用域" width="120">
          <template #default="{ row }">
            {{ scopeText(row.scope_type) }}
          </template>
        </el-table-column>

        <el-table-column prop="scope_id" label="作用域ID" width="100" />

        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '有效' : row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              link
              type="danger"
              @click="handleUnbindRole(row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="role-tip">
        说明：省级/市级/区县级机构管理员不单独建角色，由 admin + agency + agency_level 表达；群组管理员由 admin + group 表达。
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getUserList,
  createUser,
  disableUser,
  getUserRoles,
  unbindUserRole,
} from '@/api/user'
import { getAgencyList } from '@/api/agency'

const loading = ref(false)
const userList = ref<any[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const searchForm = reactive({
  keyword: '',
  status: '',
})

const showCreateDialog = ref(false)
const createLoading = ref(false)
const createFormRef = ref<FormInstance>()

const createForm = reactive({
  username: '',
  password: '123456',
  real_name: '',
  phone: '',
  email: '',
  agency_id: undefined as number | undefined,
})

const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }],
  agency_id: [{ required: true, message: '请选择所属机构', trigger: 'change' }],
}

const agencyLoading = ref(false)
const agencyList = ref<any[]>([])

const showRolesDialog = ref(false)
const userRoles = ref<any[]>([])
const currentViewUserId = ref(0)
const currentUser = ref<any | null>(null)

const activeCount = computed(() => userList.value.filter((u) => u.status === 'active').length)
const disabledCount = computed(() => userList.value.filter((u) => u.status === 'disabled').length)

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

function unwrapList<T = any>(raw: any): { items: T[]; total: number } {
  const data: any = unwrapResponse(raw)

  if (data?.items && Array.isArray(data.items)) {
    return {
      items: data.items,
      total: Number(data.total || 0),
    }
  }

  if (Array.isArray(data)) {
    return {
      items: data,
      total: data.length,
    }
  }

  return {
    items: [],
    total: 0,
  }
}

function getErrorMessage(error: any, fallback: string) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    fallback
  )
}

async function fetchUsers() {
  loading.value = true
  try {
    const raw: any = await getUserList({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
    })

    console.log('[UserManage] user list raw:', raw)

    const data = unwrapList<any>(raw)
    userList.value = data.items || []
    total.value = data.total || 0
  } catch (error: any) {
    console.error('[UserManage] 加载用户失败:', error)
    ElMessage.error(getErrorMessage(error, '加载用户列表失败'))
    userList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function fetchAgencies() {
  agencyLoading.value = true
  try {
    const raw = await getAgencyList({ page: 1, page_size: 100 })
    const data = unwrapList<any>(raw)
    agencyList.value = data.items || []
    console.log('[UserManage] agency list:', agencyList.value)
  } catch (error: any) {
    console.error('[UserManage] 加载机构失败:', error)
    ElMessage.error(getErrorMessage(error, '加载机构列表失败'))
    agencyList.value = []
  } finally {
    agencyLoading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchUsers()
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.status = ''
  page.value = 1
  fetchUsers()
}

function resetCreateForm() {
  Object.assign(createForm, {
    username: '',
    password: '123456',
    real_name: '',
    phone: '',
    email: '',
    agency_id: undefined,
  })
}

async function openCreateDialog() {
  resetCreateForm()
  showCreateDialog.value = true
  if (agencyList.value.length === 0) {
    await fetchAgencies()
  }
}

async function handleCreate() {
  await createFormRef.value?.validate()

  createLoading.value = true
  try {
    await createUser({
      username: createForm.username,
      password: createForm.password,
      real_name: createForm.real_name || undefined,
      phone: createForm.phone || undefined,
      email: createForm.email || undefined,
      agency_id: createForm.agency_id,
    })

    ElMessage.success('创建成功')
    showCreateDialog.value = false
    resetCreateForm()
    fetchUsers()
  } catch (error: any) {
    console.error('[UserManage] 创建用户失败:', error)
    ElMessage.error(getErrorMessage(error, '创建用户失败'))
  } finally {
    createLoading.value = false
  }
}

async function handleDisable(row: any) {
  await ElMessageBox.confirm(`确定停用用户 "${row.username}" 吗？`, '确认停用', {
    type: 'warning',
  })

  try {
    await disableUser(row.id)
    ElMessage.success('已停用')
    fetchUsers()
  } catch (error: any) {
    console.error('[UserManage] 停用用户失败:', error)
    ElMessage.error(getErrorMessage(error, '停用用户失败'))
  }
}

async function handleViewRoles(row: any) {
  currentViewUserId.value = row.id
  currentUser.value = row

  try {
    const raw: any = await getUserRoles(row.id)
    console.log('[UserManage] roles raw:', raw)
    const data = unwrapResponse<any[]>(raw)
    userRoles.value = Array.isArray(data) ? data : []
    showRolesDialog.value = true
  } catch (error: any) {
    console.error('[UserManage] 加载角色失败:', error)
    ElMessage.error(getErrorMessage(error, '加载用户角色失败'))
  }
}

async function handleUnbindRole(row: any) {
  await ElMessageBox.confirm('确定取消该角色？', '确认取消', { type: 'warning' })

  try {
    await unbindUserRole(currentViewUserId.value, row.id)
    ElMessage.success('已取消')
    const raw: any = await getUserRoles(currentViewUserId.value)
    const data = unwrapResponse<any[]>(raw)
    userRoles.value = Array.isArray(data) ? data : []
  } catch (error: any) {
    console.error('[UserManage] 取消角色失败:', error)
    ElMessage.error(getErrorMessage(error, '取消角色失败'))
  }
}

function formatAgencyOption(agency: any) {
  const level = agency.agency_level ? `｜${agencyLevelText(agency.agency_level)}` : ''
  return `${agency.agency_name || agency.agency_code}（ID: ${agency.id}${level}）`
}

function agencyLevelText(level: string) {
  const map: Record<string, string> = {
    national: '国家级',
    province: '省级',
    city: '市级',
    county: '区县级',
  }
  return map[level] || level
}

function statusText(status: string) {
  const map: Record<string, string> = {
    active: '正常',
    disabled: '停用',
    locked: '锁定',
    archived: '归档',
  }
  return map[status] || status || '-'
}

function statusTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    active: 'success',
    disabled: 'danger',
    locked: 'warning',
    archived: 'info',
  }
  return map[status] || 'info'
}

function scopeText(scopeType: string) {
  const map: Record<string, string> = {
    platform: '平台',
    agency: '机构',
    group: '群组',
  }
  return map[scopeType] || scopeType
}

function roleText(row: any) {
  if (row.role_code === 'admin' && row.scope_type === 'platform') return '平台管理员'
  if (row.role_code === 'admin' && row.scope_type === 'agency') return '机构管理员'
  if (row.role_code === 'admin' && row.scope_type === 'group') return '群组管理员'
  if (row.role_code === 'user' && row.scope_type === 'group') return '业务用户'
  if (row.role_code === 'governor' && row.scope_type === 'group') return '治理员'
  return row.role_code
}

function roleTagType(roleCode: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    admin: 'danger',
    user: 'success',
    governor: 'warning',
  }
  return map[roleCode] || 'info'
}

onMounted(() => {
  fetchUsers()
  fetchAgencies()
})
</script>

<style scoped>
.user-manage-view {
  min-height: 100%;
  padding: 20px;
  background: #f5f7fb;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.page-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.summary-row {
  margin-bottom: 14px;
}

.summary-card {
  padding: 14px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.summary-value {
  font-size: 22px;
  font-weight: 700;
  color: #2563eb;
}

.summary-label {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.section-card {
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.search-form {
  margin-bottom: -18px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
}

.total-text {
  font-size: 13px;
  color: #6b7280;
}

.muted-text {
  margin-left: 4px;
  color: #9ca3af;
  font-size: 12px;
}

.dialog-alert {
  margin-bottom: 16px;
}

.form-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.role-user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  margin-bottom: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.role-user-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.role-user-meta {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.role-tip {
  margin-top: 16px;
  padding: 12px;
  font-size: 13px;
  color: #6b7280;
  background: #f8fafc;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
}
</style>
