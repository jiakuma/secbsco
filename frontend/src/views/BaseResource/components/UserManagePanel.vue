<template>
  <div class="manage-panel">
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="用户名 / 姓名 / 手机 / 邮箱" clearable style="width: 250px" @keyup.enter="loadList" />
        </el-form-item>
        <el-form-item label="所属机构">
          <el-cascader
            v-model="searchForm.agency_path"
            :options="agencyTreeOptions"
            :props="{value:'id',label:'agency_name',children:'children',checkStrictly:true,emitPath:false,expandTrigger:'hover'}"
            clearable
            filterable
            placeholder="全部机构"
            style="width: 260px"
            @visible-change="handleCascaderVisibleChange"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role_code" clearable placeholder="全部角色" style="width: 130px">
            <el-option label="管理员" value="admin" />
            <el-option label="业务用户" value="user" />
            <el-option label="治理员" value="governor" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
            <el-option label="锁定" value="locked" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button type="success" @click="openCreateDialog">新增用户</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="userList" stripe border v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="real_name" label="姓名" min-width="120" />
        <el-table-column prop="agency_name" label="所属机构" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="角色" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-for="r in normalizeRoles(row.roles, row.role_code)"
              :key="r.role_code"
              class="role-tag"
              size="small"
              :type="roleTagType(r.role_code)"
            >
              {{ roleCodeText(r.role_code) }}
            </el-tag>
            <span v-if="normalizeRoles(row.roles, row.role_code).length === 0" class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }"><el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.status !== 'active'" link type="success" @click="handleEnable(row)">启用</el-button>
            <el-button v-else link type="warning" @click="handleDisable(row)">禁用</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <span class="total-text">Total {{ total }}</span>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="sizes, prev, pager, next, jumper" @current-change="loadList" @size-change="loadList" />
      </div>
    </el-card>

    <el-dialog v-model="formDialogVisible" :title="formMode === 'create' ? '新增用户' : '编辑用户'" width="680px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="用户名" prop="username"><el-input v-model="form.username" :disabled="formMode === 'edit'" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="初始密码" prop="password"><el-input v-model="form.password" type="password" show-password :disabled="formMode === 'edit'" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="姓名"><el-input v-model="form.real_name" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="所属机构" prop="agency_id">
              <el-cascader
                v-model="form.agency_id"
                :options="agencyTreeOptions"
                :props="{value:'id',label:'agency_name',children:'children',checkStrictly:true,emitPath:false,expandTrigger:'hover'}"
                clearable
                filterable
                placeholder="请选择所属机构"
                style="width:100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="手机号"><el-input v-model="form.phone" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="角色" prop="role_code">
              <el-select v-model="form.role_code" placeholder="请选择角色" style="width:100%">
                <el-option label="管理员" value="admin" />
                <el-option label="业务用户" value="user" />
                <el-option label="治理员" value="governor" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="formDialogVisible=false">取消</el-button><el-button type="primary" :loading="submitLoading" @click="submitForm">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="用户详情" width="620px">
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="用户名">{{ detail.username }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ detail.real_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="所属机构">{{ detail.agency_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ detail.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detail.email || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { getAgencyTree } from '@/api/agency'
import { bindUserRole, createUser, deleteUserAsDisable, disableUser, enableUser, getUserDetail, getUserList, getUserRoles, unbindUserRole, updateUser } from '@/api/user'

const emit = defineEmits<{ (e: 'summary-change', payload: { total: number }): void }>()
const loading = ref(false); const submitLoading = ref(false)
const userList = ref<any[]>([]); const agencyTreeOptions = ref<any[]>([])
const total = ref(0); const page = ref(1); const pageSize = ref(10)
const formDialogVisible = ref(false); const detailVisible = ref(false)
const formMode = ref<'create'|'edit'>('create'); const editingId = ref<number|null>(null); const detail = ref<any>(null)
const formRef = ref<FormInstance>()
const searchForm = reactive<any>({ keyword:'', status:'', agency_path: undefined, role_code:'' })
const form = reactive<any>({})

function safeParseJson(value: string | null) {
  if (!value) return null
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

const isPlatformAdmin = computed(() => {
  const roles = safeParseJson(localStorage.getItem('user_roles'))
  if (Array.isArray(roles)) {
    return roles.some((role: any) => role?.role_code === 'admin' && role?.scope_type === 'platform')
  }

  const userInfo = safeParseJson(localStorage.getItem('user_info'))
  const userRoles = userInfo?.roles || userInfo?.role_bindings || userInfo?.roleBindings
  if (Array.isArray(userRoles)) {
    return userRoles.some((role: any) => role?.role_code === 'admin' && role?.scope_type === 'platform')
  }

  const permissions = safeParseJson(localStorage.getItem('user_permissions'))
  return Array.isArray(permissions) && permissions.includes('role:grant')
})

const currentUserAgencyId = computed(() => {
  const userInfo = safeParseJson(localStorage.getItem('user_info'))
  return userInfo?.agency_id || userInfo?.agency?.id || null
})

const formRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }],
  agency_id: [{
    validator: (_rule, value, callback) => {
      if (!value) callback(new Error('请选择所属机构'))
      else callback()
    },
    trigger: 'change',
  }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
}
function unwrap(res:any){ return res?.data ?? res }
function resetForm(){ Object.keys(form).forEach(k=>delete form[k]); Object.assign(form,{username:'',password:'123456',real_name:'',phone:'',email:'',agency_id:currentUserAgencyId.value || null,status:'active',role_code:'user'}) }
async function loadAgencyTree(){ const res:any=await getAgencyTree(); agencyTreeOptions.value=unwrap(res)||[] }
async function loadList(){
  loading.value=true
  try{
    const params:any={...searchForm,page:page.value,page_size:pageSize.value}
    if(searchForm.agency_path) params.agency_id=searchForm.agency_path
    delete params.agency_path
    const res:any=await getUserList(params)
    const data=unwrap(res)
    userList.value=data.items||[]
    total.value=data.total||0
    emit('summary-change',{total:total.value})
  } finally{
    loading.value=false
  }
}
function handleSearch(){ page.value=1; loadList() }
function resetSearch(){ Object.assign(searchForm,{keyword:'',status:'',agency_path:undefined,role_code:''}); handleSearch() }
function openCreateDialog(){ formMode.value='create'; editingId.value=null; resetForm(); formDialogVisible.value=true }

function getPrimaryRoleCode(roles:any[] = [], fallback?: string) {
  const normalized = normalizeRoles(roles, fallback)
  return normalized[0]?.role_code || fallback || 'user'
}

function getRoleScopePayload(roleCode: string, agencyId?: number | null) {
  // 平台管理员账号保留平台级管理员作用域；其他用户统一使用机构作用域。
  if (roleCode === 'admin' && !agencyId) {
    return { role_code: roleCode, scope_type: 'platform', scope_id: null }
  }
  return {
    role_code: roleCode,
    scope_type: 'agency',
    scope_id: agencyId || currentUserAgencyId.value,
  }
}

async function syncUserRole(userId: number, roleCode: string, agencyId?: number | null) {
  const targetRole = getRoleScopePayload(roleCode, agencyId)
  const res:any = await getUserRoles(userId)
  const roles = unwrap(res) || []
  const activeRoles = Array.isArray(roles) ? roles.filter((role:any) => role.status === 'active') : []

  const targetExists = activeRoles.some((role:any) =>
    role.role_code === targetRole.role_code
    && role.scope_type === targetRole.scope_type
    && (role.scope_id ?? null) === (targetRole.scope_id ?? null)
  )

  for (const role of activeRoles) {
    const isTarget =
      role.role_code === targetRole.role_code
      && role.scope_type === targetRole.scope_type
      && (role.scope_id ?? null) === (targetRole.scope_id ?? null)

    if (!isTarget && role.id) {
      await unbindUserRole(userId, role.id)
    }
  }

  if (!targetExists) {
    await bindUserRole(userId, targetRole)
  }
}

function openEditDialog(row:any){
  formMode.value='edit'
  editingId.value=row.id
  resetForm()
  Object.assign(form,row)
  form.password='******'
  form.role_code = getPrimaryRoleCode(row.roles, row.role_code)
  formDialogVisible.value=true
}
async function submitForm(){
  await formRef.value?.validate()
  submitLoading.value=true
  try{
    const payload={...form}
    if (!isPlatformAdmin.value && !payload.agency_id) {
      payload.agency_id = currentUserAgencyId.value
    }

    const roleCode = payload.role_code || 'user'
    delete payload.role_code

    if(formMode.value==='edit') {
      delete payload.password
      if(editingId.value) {
        await updateUser(editingId.value,payload)
        await syncUserRole(editingId.value, roleCode, payload.agency_id)
      }
    } else {
      const res:any = await createUser(payload)
      const createdUser = unwrap(res)
      const createdUserId = createdUser?.id
      if (createdUserId) {
        await syncUserRole(createdUserId, roleCode, payload.agency_id)
      }
    }

    ElMessage.success('保存成功')
    formDialogVisible.value=false
    await loadList()
  } finally{
    submitLoading.value=false
  }
}
async function openDetail(row:any){ const res:any=await getUserDetail(row.id); detail.value=unwrap(res); detailVisible.value=true }
async function handleEnable(row:any){ await enableUser(row.id); ElMessage.success('已启用'); await loadList() }
async function handleDisable(row:any){ await ElMessageBox.confirm(`确认禁用用户「${row.username}」？`,'提示',{type:'warning'}); await disableUser(row.id); ElMessage.success('已禁用'); await loadList() }
async function handleDelete(row:any){
  await ElMessageBox.confirm(`确认物理删除用户「${row.username}」？该用户的角色绑定和群组关系将一并删除。`,'删除确认',{type:'warning'})
  await deleteUserAsDisable(row.id)
  ElMessage.success('已删除')
  await loadList()
}
function statusText(v:string){ return ({active:'启用',disabled:'禁用',locked:'锁定'} as any)[v]||v||'-' }
function statusTagType(v:string):'success'|'info'|'warning'|'danger'{ return v==='active'?'success':v==='locked'?'warning':'info' }
function roleTagType(v:string):'success'|'info'|'warning'|'danger'{ return v==='admin'?'danger':v==='governor'?'warning':'success' }
function roleCodeText(v:string){ return ({admin:'管理员',user:'业务用户',governor:'治理员'} as any)[v]||v }
function normalizeRoles(roles:any[] = [], fallback?: string) {
  const order = ['admin', 'user', 'governor']
  const roleSet = new Set<string>()
  roles.forEach((role:any) => {
    if (role?.role_code) roleSet.add(role.role_code)
  })
  if (roleSet.size === 0 && fallback) {
    roleSet.add(fallback)
  }
  return order.filter(roleCode => roleSet.has(roleCode)).map(roleCode => ({ role_code: roleCode }))
}
function handleCascaderVisibleChange(visible:boolean){ if(visible) searchForm.agency_path=undefined }
onMounted(async()=>{ await loadAgencyTree(); await loadList() })
</script>

<style scoped>
.manage-panel{padding-top:8px}.filter-card{margin-bottom:12px;border-radius:12px}.pagination{display:flex;align-items:center;justify-content:space-between;margin-top:14px}.total-text,.muted{color:#64748b;font-size:13px}.role-tag{margin:2px}.role-user-line{margin-bottom:12px;color:#334155;font-weight:600}
</style>
