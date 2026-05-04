<template>
  <div class="task-page">
    <div class="page-header">
      <div>
        <h2>联合统计任务</h2>
        <p>创建、执行并查看多机构联合统计任务</p>
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

        <el-form-item>
          <el-button type="primary" @click="loadTasks">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table
        v-loading="loading"
        :data="taskList"
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="task_code" label="任务编号" min-width="180" />
        <el-table-column prop="task_name" label="任务名称" min-width="180" />

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

        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row.id)">
              详情
            </el-button>

            <el-button
              link
              type="success"
              :loading="runningTaskId === row.id"
              @click="handleRun(row)"
            >
              执行
            </el-button>

            <el-button link type="warning" @click="goResult(row.id)">
              结果
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
      title="新建联合统计任务"
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

        <el-form-item label="统计模板ID" prop="template_id">
          <el-input-number
            v-model="createForm.template_id"
            :min="1"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="创建机构ID" prop="creator_agency_id">
          <el-input-number
            v-model="createForm.creator_agency_id"
            :min="1"
            style="width: 100%"
          />
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
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createTask,
  getTaskList,
  getTaskResult,
  runTask,
  type CreateTaskPayload,
} from '@/api/task'

const router = useRouter()

const loading = ref(false)
const creating = ref(false)
const runningTaskId = ref<number | string | null>(null)

const taskList = ref<any[]>([])
const total = ref(0)

const queryForm = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: '',
})

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()

const statRange = ref<string[]>([])

const createForm = reactive<CreateTaskPayload>({
  task_code: '',
  task_name: '',
  template_id: 1,
  creator_agency_id: 1,
  stat_start_time: '',
  stat_end_time: '',
  description: '',
})

const createRules: FormRules = {
  task_code: [{ required: true, message: '请输入任务编号', trigger: 'blur' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
}

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
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
  loadTasks()
}

function openCreateDialog() {
  createDialogVisible.value = true
  createForm.task_code = `FLU_TASK_${Date.now()}`
  createForm.task_name = ''
  createForm.template_id = 1
  createForm.creator_agency_id = 1
  createForm.description = ''
  statRange.value = []
}

async function handleCreate() {
  if (!createFormRef.value) return

  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    creating.value = true
    try {
      createForm.stat_start_time = statRange.value?.[0] || ''
      createForm.stat_end_time = statRange.value?.[1] || ''

      await createTask({ ...createForm })

      ElMessage.success('任务创建成功')
      createDialogVisible.value = false
      loadTasks()
    } catch (error) {
      console.error(error)
      ElMessage.error('任务创建失败，请检查后端任务创建字段')
    } finally {
      creating.value = false
    }
  })
}

function goDetail(taskId: number | string) {
  router.push(`/tasks/${taskId}`)
}

async function handleRun(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认执行任务「${row.task_name || row.task_code}」吗？`,
      '执行确认',
      {
        type: 'warning',
        confirmButtonText: '执行',
        cancelButtonText: '取消',
      },
    )

    runningTaskId.value = row.id
    await runTask(row.id)

    ElMessage.success('任务执行成功')
    loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('任务执行失败')
    }
  } finally {
    runningTaskId.value = null
  }
}

async function goResult(taskId: number | string) {
  try {
    await getTaskResult(taskId)
    router.push(`/tasks/${taskId}?tab=result`)
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
  }

  return map[status] || 'info'
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

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>