<template>
  <div class="manage-panel">
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="机构编码 / 机构名称" clearable style="width: 220px" @keyup.enter="loadList" />
        </el-form-item>
        <el-form-item label="机构层级">
          <el-select v-model="searchForm.agency_level" placeholder="全部" clearable style="width: 150px">
            <el-option label="国家级" value="national" />
            <el-option label="省级" value="province" />
            <el-option label="市级" value="city" />
            <el-option label="区县级" value="county" />
          </el-select>
        </el-form-item>
        <el-form-item label="机构类型">
          <el-select v-model="searchForm.agency_type" placeholder="全部" clearable style="width: 150px">
            <el-option label="疾控" value="cdc" />
            <el-option label="卫健委" value="health_commission" />
            <el-option label="科研机构" value="research" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 130px">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button type="success" @click="openCreateDialog()">新增机构</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
          <el-table :data="agencyList" stripe border v-loading="loading" style="width: 100%">
            <el-table-column prop="agency_name" label="机构名称" min-width="180" show-overflow-tooltip />
            <el-table-column prop="agency_code" label="机构编码" min-width="150" show-overflow-tooltip />
            <el-table-column prop="agency_level" label="层级" width="100">
              <template #default="{ row }">{{ levelText(row.agency_level) }}</template>
            </el-table-column>
            <el-table-column prop="agency_type" label="类型" width="110">
              <template #default="{ row }">{{ typeText(row.agency_type) }}</template>
            </el-table-column>
            <el-table-column prop="parent_agency_name" label="上级机构" min-width="150" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">详情</el-button>
                <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                <el-button v-if="row.status === 'active'" link type="warning" @click="handleDisable(row)">停用</el-button>
                <el-button v-if="row.status === 'disabled'" link type="success" @click="handleEnable(row)">启用</el-button>
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
          @current-change="loadList"
          @size-change="loadList"
        />
      </div>
    </el-card>

    <el-dialog v-model="formDialogVisible" :title="formMode === 'create' ? '新增机构' : '编辑机构'" width="720px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="机构编码" prop="agency_code">
              <el-input v-model="form.agency_code" :disabled="formMode === 'edit'" placeholder="请输入机构编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="机构名称" prop="agency_name">
              <el-input v-model="form.agency_name" placeholder="请输入机构名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="机构层级" prop="agency_level">
              <el-select v-model="form.agency_level" placeholder="请选择" style="width: 100%">
                <el-option label="国家级" value="national" />
                <el-option label="省级" value="province" />
                <el-option label="市级" value="city" />
                <el-option label="区县级" value="county" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="机构类型" prop="agency_type">
              <el-select v-model="form.agency_type" placeholder="请选择" style="width: 100%">
                <el-option label="疾控" value="cdc" />
                <el-option label="卫健委" value="health_commission" />
                <el-option label="科研机构" value="research" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="上级机构" prop="parent_agency_id">
          <el-select v-model="form.parent_agency_id" filterable clearable placeholder="请选择上级机构" style="width: 100%">
            <el-option v-for="agency in agencyOptions" :key="agency.id" :label="formatAgencyOption(agency)" :value="agency.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="行政区划代码">
              <el-input v-model="form.region_code" placeholder="如 110108" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="行政区划名称">
              <el-input v-model="form.region_name" placeholder="如 北京市海淀区" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="form.contact_person" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="机构详情" width="680px">
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="机构名称">{{ detail.agency_name }}</el-descriptions-item>
        <el-descriptions-item label="机构编码">{{ detail.agency_code }}</el-descriptions-item>
        <el-descriptions-item label="机构层级">{{ levelText(detail.agency_level) }}</el-descriptions-item>
        <el-descriptions-item label="机构类型">{{ typeText(detail.agency_type) }}</el-descriptions-item>
        <el-descriptions-item label="上级机构">{{ detail.parent_agency_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
        <el-descriptions-item label="联系人">{{ detail.contact_person || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.contact_phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ detail.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { createAgency, deleteAgency, disableAgency, enableAgency, getAgencyDetail, getAgencyList, updateAgency } from '@/api/agency'

const emit = defineEmits<{ (e: 'summary-change', payload: { total: number }): void }>()

const loading = ref(false)
const submitLoading = ref(false)
const agencyList = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const formDialogVisible = ref(false)
const detailVisible = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const detail = ref<any>(null)
const formRef = ref<FormInstance>()

const searchForm = reactive<any>({ keyword: '', agency_level: '', agency_type: '', status: '' })
const form = reactive<any>({})

const agencyOptions = computed(() => agencyList.value.filter((agency: any) => agency.id !== editingId.value))

const formRules: FormRules = {
  agency_code: [{ required: true, message: '请输入机构编码', trigger: 'blur' }],
  agency_name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  agency_level: [{ required: true, message: '请选择机构层级', trigger: 'change' }],
}

function resetForm() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, {
    agency_code: '', agency_name: '', agency_type: '', agency_level: '', parent_agency_id: null,
    region_code: '', region_name: '', contact_person: '', contact_phone: '', description: '', status: 'active',
  })
}

function unwrap(res: any) { return res?.data ?? res }

async function loadList() {
  loading.value = true
  try {
    const params = { ...searchForm, page: page.value, page_size: pageSize.value }
    const res: any = await getAgencyList(params)
    const data = unwrap(res)
    agencyList.value = data.items || []
    total.value = data.total || 0
    emit('summary-change', { total: total.value })
  } finally { loading.value = false }
}

function handleSearch() { page.value = 1; loadList() }
function resetSearch() { Object.assign(searchForm, { keyword: '', agency_level: '', agency_type: '', status: '' }); handleSearch() }
function openCreateDialog(parent?: any) {
  formMode.value = 'create'; editingId.value = null; resetForm()
  if (parent?.id) form.parent_agency_id = parent.id
  formDialogVisible.value = true
}

function openEditDialog(row: any) {
  formMode.value = 'edit'; editingId.value = row.id; resetForm(); Object.assign(form, row); formDialogVisible.value = true
}

async function submitForm() {
  await formRef.value?.validate()
  submitLoading.value = true
  try {
    const payload = { ...form }
    if (formMode.value === 'create') await createAgency(payload)
    else if (editingId.value) await updateAgency(editingId.value, payload)
    ElMessage.success('保存成功')
    formDialogVisible.value = false
    await loadList()
  } finally { submitLoading.value = false }
}

async function openDetail(row: any) {
  const res: any = await getAgencyDetail(row.id)
  detail.value = unwrap(res)
  detailVisible.value = true
}

async function handleEnable(row: any) {
  await ElMessageBox.confirm(`确认启用机构「${row.agency_name}」？`, '启用确认', { type: 'success' })
  await enableAgency(row.id)
  ElMessage.success('已启用')
  await loadList()
}

async function handleDisable(row: any) {
  await ElMessageBox.confirm(`确认停用机构「${row.agency_name}」？停用后该机构暂不可参与后续业务配置。`, '停用确认', { type: 'warning' })
  await disableAgency(row.id)
  ElMessage.success('已停用')
  await loadList()
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认物理删除机构「${row.agency_name}」？该机构及下级机构、关联用户、节点和关系数据将一并删除。`, '提示', { type: 'warning' })
  await deleteAgency(row.id)
  ElMessage.success('已删除')
  await loadList()
}

function levelText(v: string) { return ({ national: '国家级', province: '省级', city: '市级', county: '区县级' } as any)[v] || v || '-' }
function typeText(v: string) { return ({ cdc: '疾控', hospital: '医院', lab: '实验室', health_commission: '卫健委', research: '科研机构', other: '其他' } as any)[v] || v || '-' }
function statusText(v: string) { return ({ active: '启用', disabled: '停用' } as any)[v] || v || '-' }
function statusTagType(v: string): 'success' | 'info' | 'warning' | 'danger' { return v === 'active' ? 'success' : v === 'disabled' ? 'info' : 'danger' }
function formatAgencyOption(a: any) { return `${a.agency_name}（${a.agency_code}）` }

onMounted(async () => { await loadList() })
</script>

<style scoped>
.manage-panel { padding-top: 8px; }
.filter-card { margin-bottom: 12px; border-radius: 12px; }
.table-card { border-radius: 12px; }
.pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; }
.total-text { color: #64748b; font-size: 13px; }
</style>
