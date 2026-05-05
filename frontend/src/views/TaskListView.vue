<template>
  <div class="task-page">
    <div class="page-header">
      <div>
        <h2>任务中心</h2>
        <p>统一管理联合统计任务，并为后续联邦学习任务预留入口</p>
      </div>

      <div class="header-actions">
        <el-button @click="loadTasks">刷新</el-button>
        <el-button type="primary" @click="openCreateDialog">新建任务</el-button>
      </div>
    </div>

    <el-card class="query-card" shadow="never">
      <el-form :inline="true" :model="queryForm">
        <el-form-item label="任务名称">
          <el-input
            v-model="queryForm.keyword"
            placeholder="请输入任务名称或编号"
            clearable
            style="width: 220px"
            @keyup.enter="loadTasks"
          />
        </el-form-item>

        <el-form-item label="任务状态">
          <el-select
            v-model="queryForm.status"
            placeholder="全部状态"
            clearable
            style="width: 160px"
          >
            <el-option label="已创建" value="created" />
            <el-option label="执行中" value="running" />
            <el-option label="执行成功" value="success" />
            <el-option label="执行失败" value="failed" />
          </el-select>
        </el-form-item>

        <el-form-item label="任务类型">
          <el-select
            v-model="queryForm.task_type"
            placeholder="全部类型"
            clearable
            style="width: 160px"
          >
            <el-option label="联合统计" value="statistic" />
            <el-option label="联邦学习" value="federated_learning" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadTasks">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="filteredTaskList"
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="task_code" label="任务编号" min-width="180" />
        <el-table-column prop="task_name" label="任务名称" min-width="180" />

        <el-table-column label="任务类型" width="130">
          <template #default="{ row }">
            <el-tag :type="getTaskTypeTagType(row)">
              {{ getTaskTypeText(row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="template_id" label="模板ID" width="100" />
        <el-table-column prop="stat_start_time" label="统计开始时间" min-width="170" />
        <el-table-column prop="stat_end_time" label="统计结束时间" min-width="170" />
        <el-table-column prop="created_at" label="创建时间" min-width="170" />

      <el-table-column label="操作" width="300" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="goDetail(row.id)">
            详情
          </el-button>

          <el-button
            link
            type="success"
            :loading="runningTaskId === row.id"
            :disabled="!canRunTask(row)"
            @click="handleRun(row)"
          >
            {{ getRunButtonText(row) }}
          </el-button>

          <el-button
            link
            :type="row.status === 'success' ? 'warning' : 'info'"
            @click="goResult(row)"
          >
            {{ row.status === 'success' ? '查看结果' : '结果' }}
          </el-button>
        </template>
      </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :page-size="queryForm.page_size"
          v-model:current-page="queryForm.page"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="createDialogVisible"
      title="新建任务"
      width="640px"
      destroy-on-close
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="120px"
      >
        <el-form-item label="任务编号" prop="task_code">
          <el-input v-model="createForm.task_code" placeholder="例如 FLU_TASK_20260504_001" />
        </el-form-item>

        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="createForm.task_name" placeholder="例如 流感样病例联合统计任务" />
        </el-form-item>

        <el-form-item label="任务类型" prop="task_type">
          <el-select
            v-model="createForm.task_type"
            placeholder="请选择任务类型"
            style="width: 100%"
          >
            <el-option label="联合统计" value="statistic" />
            <el-option label="联邦学习（待开发）" value="federated_learning" disabled />
          </el-select>
          <div class="form-tip">
            当前阶段先支持联合统计；联邦学习将在任务模型设计完成后开放。
          </div>
        </el-form-item>

        <el-form-item label="统计模板" prop="template_id">
          <el-select
            v-model="createForm.template_id"
            placeholder="请选择统计模板"
            filterable
            clearable
            style="width: 100%"
            :loading="templateLoading"
          >
            <el-option
              v-for="item in templateOptions"
              :key="item.id"
              :label="item.template_name || item.name || item.template_code || `模板${item.id}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="创建机构" prop="creator_agency_id">
          <el-select
            v-model="createForm.creator_agency_id"
            placeholder="请选择创建机构"
            filterable
            clearable
            style="width: 100%"
            :loading="agencyLoading"
          >
            <el-option
              v-for="item in agencyOptions"
              :key="item.id"
              :label="item.agency_name || item.name || item.agency_code || `机构${item.id}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="统计时间范围">
          <el-date-picker
            v-model="statRange"
            type="datetimerange"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务描述"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { getAgencyList } from '@/api/agency'
import { getStatTemplateList } from '@/api/statTemplate'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createTask,
  getTaskList,
  getTaskResult,
  runTask,
  type CreateTaskPayload,
} from '@/api/task'

type TaskType = 'statistic' | 'federated_learning'

const router = useRouter()

const loading = ref(false)
const creating = ref(false)
const runningTaskId = ref<number | string | null>(null)

const taskList = ref<any[]>([])
const total = ref(0)

const agencyOptions = ref<any[]>([])
const templateOptions = ref<any[]>([])

const agencyLoading = ref(false)
const templateLoading = ref(false)

const queryForm = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: '',
  task_type: '',
})

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()

const statRange = ref<string[]>([])

const createForm = reactive<CreateTaskPayload & { task_type: TaskType }>({
  task_code: '',
  task_name: '',
  task_type: 'statistic',
  template_id: null,
  creator_agency_id: null,
  stat_start_time: '',
  stat_end_time: '',
  description: '',
})

const createRules: FormRules = {
  task_code: [{ required: true, message: '请输入任务编号', trigger: 'blur' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  template_id: [{ required: true, message: '请选择统计模板', trigger: 'change' }],
  creator_agency_id: [{ required: true, message: '请选择创建机构', trigger: 'change' }],
}

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

function parseJsonObject(value: any) {
  if (!value) return {}

  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return {}
    }
  }

  if (typeof value === 'object') {
    return value
  }

  return {}
}

function getTaskType(row: any): TaskType {
  const paramsJson = parseJsonObject(row?.params_json)
  return (row?.task_type || paramsJson.task_type || 'statistic') as TaskType
}

function getTaskTypeText(row: any) {
  const map: Record<TaskType, string> = {
    statistic: '联合统计',
    federated_learning: '联邦学习',
  }

  return map[getTaskType(row)] || '联合统计'
}

function getTaskTypeTagType(row: any) {
  return getTaskType(row) === 'federated_learning' ? 'warning' : 'success'
}

function isFederatedLearningTask(row: any) {
  return getTaskType(row) === 'federated_learning'
}

function normalizeList(payload: any) {
  if (Array.isArray(payload)) {
    return {
      list: payload,
      total: payload.length,
    }
  }

  if (Array.isArray(payload?.items)) {
    return {
      list: payload.items,
      total: payload.total ?? payload.items.length,
    }
  }

  if (Array.isArray(payload?.list)) {
    return {
      list: payload.list,
      total: payload.total ?? payload.list.length,
    }
  }

  if (Array.isArray(payload?.records)) {
    return {
      list: payload.records,
      total: payload.total ?? payload.records.length,
    }
  }

  return {
    list: [],
    total: 0,
  }
}


const filteredTaskList = computed(() => {
  if (!queryForm.task_type) {
    return taskList.value
  }

  return taskList.value.filter((item) => getTaskType(item) === queryForm.task_type)
})

async function loadAgencyOptions() {
  agencyLoading.value = true

  try {
    const res = await getAgencyList({
      page: 1,
      page_size: 100,
    })

    const payload = unwrapResponse(res)
    const normalized = normalizeList(payload)

    agencyOptions.value = normalized.list
  } catch (error) {
    console.error(error)
    ElMessage.error('机构列表加载失败')
  } finally {
    agencyLoading.value = false
  }
}

async function loadTemplateOptions() {
  templateLoading.value = true

  try {
    const res = await getStatTemplateList({
      page: 1,
      page_size: 100,
    })

    const payload = unwrapResponse(res)
    const normalized = normalizeList(payload)

    templateOptions.value = normalized.list
  } catch (error) {
    console.error(error)
    ElMessage.error('统计模板列表加载失败')
  } finally {
    templateLoading.value = false
  }
}


async function loadTasks() {
  loading.value = true
  try {
    const res = await getTaskList({
      page: queryForm.page,
      page_size: queryForm.page_size,
      keyword: queryForm.keyword || undefined,
      status: queryForm.status || undefined,
    })

    const payload = unwrapResponse(res)
    const normalized = normalizeList(payload)

    taskList.value = normalized.list
    total.value = normalized.total
  } catch (error) {
    console.error(error)
    ElMessage.error('任务列表加载失败')
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  queryForm.page = 1
  queryForm.keyword = ''
  queryForm.status = ''
  queryForm.task_type = ''
  loadTasks()
}

async function openCreateDialog() {
  createDialogVisible.value = true

  createForm.task_code = `FLU_TASK_${Date.now()}`
  createForm.task_name = ''
  createForm.task_type = 'statistic'
  createForm.template_id = null
  createForm.creator_agency_id = null
  createForm.stat_start_time = ''
  createForm.stat_end_time = ''
  createForm.description = ''
  statRange.value = []

  await Promise.all([
    loadAgencyOptions(),
    loadTemplateOptions(),
  ])
}

async function handleCreate() {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    if (!createForm.template_id) {
      ElMessage.warning('请选择统计模板')
      return
    }

    if (!createForm.creator_agency_id) {
      ElMessage.warning('请选择创建机构')
      return
    }

    creating.value = true

    try {
      const payload: CreateTaskPayload = {
        task_code: createForm.task_code,
        task_name: createForm.task_name,
        template_id: createForm.template_id,
        creator_agency_id: createForm.creator_agency_id,
        description: createForm.description || undefined,
        stat_start_time: statRange.value?.[0] || undefined,
        stat_end_time: statRange.value?.[1] || undefined,
        params_json: {
          task_type: createForm.task_type,
        },
      }

      await createTask(payload)

      ElMessage.success('任务创建成功')
      createDialogVisible.value = false
      await loadTasks()
    } catch (error) {
      console.error(error)
      ElMessage.error('任务创建失败，请检查统计模板、创建机构和任务编号是否有效')
    } finally {
      creating.value = false
    }
  })
}

function goDetail(taskId: number | string) {
  router.push(`/tasks/${taskId}`)
}

async function handleRun(row: any) {
  if (isFederatedLearningTask(row)) {
    ElMessage.warning('联邦学习任务执行能力待开发')
    return
  }

  if (row.status === 'success') {
    ElMessage.info('该任务已执行成功，如需重新执行请先调整任务状态')
    return
  }

  if (row.status === 'running') {
    ElMessage.warning('该任务正在执行中，请稍后刷新查看状态')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认执行任务「${row.task_name || row.task_code}」吗？`,
      '执行确认',
      {
        type: 'warning',
        confirmButtonText: row.status === 'failed' ? '重新执行' : '执行',
        cancelButtonText: '取消',
      },
    )

    runningTaskId.value = row.id

    await runTask(row.id)

    ElMessage.success('任务执行成功')

    await loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('任务执行失败，请检查任务参与方配置')
    }
  } finally {
    runningTaskId.value = null
  }
}


async function goResult(row: any) {
  if (isFederatedLearningTask(row)) {
    ElMessage.warning('联邦学习任务结果展示待开发')
    return
  }

  if (row.status !== 'success') {
    ElMessage.warning('当前任务暂无统计结果，请先执行任务')
    return
  }

  try {
    await getTaskResult(row.id)
    router.push(`/tasks/${row.id}?tab=result`)
  } catch (error) {
    console.error(error)
    ElMessage.warning('当前任务暂无统计结果，请先执行任务')
  }
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    created: '已创建',
    pending: '待执行',
    running: '执行中',
    success: '成功',
    failed: '失败',
    canceled: '已取消',
  }

  return map[status] || status || '-'
}

function getStatusType(status: string) {
  const map: Record<string, string> = {
    created: 'info',
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    canceled: 'info',
  }

  return map[status] || 'info'
}

function canRunTask(row: any) {
  if (isFederatedLearningTask(row)) return false
  return ['created', 'pending', 'failed'].includes(row.status)
}

function getRunButtonText(row: any) {
  if (isFederatedLearningTask(row)) return '待开发'
  if (runningTaskId.value === row.id) return '执行中'
  if (row.status === 'success') return '已执行'
  if (row.status === 'running') return '执行中'
  if (row.status === 'failed') return '重新执行'
  return '执行'
}



onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.task-page {
  padding: 24px;
  background: #f5f7fb;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  color: #1f2d3d;
}

.page-header p {
  margin: 6px 0 0;
  color: #7a8499;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.query-card {
  margin-bottom: 16px;
}

.form-tip {
  margin-top: 6px;
  color: #8c96a8;
  font-size: 12px;
  line-height: 1.4;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>