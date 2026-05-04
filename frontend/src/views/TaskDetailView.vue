<template>
  <div class="task-detail-page">
    <div class="page-header">
      <div>
        <h2>任务详情</h2>
        <p>查看联合统计任务配置、执行状态和统计结果</p>
      </div>

      <div class="header-actions">
        <el-button @click="goBack">返回列表</el-button>
        <el-button type="success" :loading="running" @click="handleRun">
          执行任务
        </el-button>
      </div>
    </div>

    <el-card v-loading="loading" shadow="never">
      <template #header>
        <div class="card-title">基础信息</div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">
          {{ taskDetail?.id || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="任务状态">
          <el-tag :type="getStatusType(taskDetail?.status)">
            {{ getStatusText(taskDetail?.status) }}
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="任务编号">
          {{ taskDetail?.task_code || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="任务名称">
          {{ taskDetail?.task_name || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="统计模板ID">
          {{ taskDetail?.template_id || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="创建机构ID">
          {{ taskDetail?.creator_agency_id || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="统计开始时间">
          {{ taskDetail?.stat_start_time || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="统计结束时间">
          {{ taskDetail?.stat_end_time || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="创建时间">
          {{ taskDetail?.created_at || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="更新时间">
          {{ taskDetail?.updated_at || '-' }}
        </el-descriptions-item>

        <el-descriptions-item label="任务描述" :span="2">
          {{ taskDetail?.description || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="section-card" shadow="never">
    <template #header>
      <div class="result-header">
        <div class="card-title">参与方信息</div>
        <el-button type="primary" plain @click="openPartyDialog">
          新增参与方
        </el-button>
      </div>
    </template>

      <el-table :data="partyList" border style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="agency_id" label="机构ID" width="120" />
        <el-table-column prop="node_id" label="节点ID" width="120" />
        <el-table-column prop="dataset_id" label="数据集ID" width="120" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170" />
      </el-table>

      <el-empty v-if="!partyList.length" description="暂无参与方数据" />
    </el-card>

    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="result-header">
          <div class="card-title">统计结果</div>
          <el-button type="primary" plain @click="loadResult">
            刷新结果
          </el-button>
        </div>
      </template>

      <template v-if="taskResult">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="结果ID">
            {{ taskResult.id || '-' }}
          </el-descriptions-item>

          <el-descriptions-item label="结果状态">
            {{ taskResult.status || '-' }}
          </el-descriptions-item>

          <el-descriptions-item label="结果Hash">
            {{ taskResult.result_hash || '-' }}
          </el-descriptions-item>

          <el-descriptions-item label="创建时间">
            {{ taskResult.created_at || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="json-title">结果内容</div>

        <pre class="json-view">{{ formatJson(taskResult.result_json || taskResult.metrics_json || taskResult) }}</pre>
      </template>

      <el-empty v-else description="暂无统计结果，请先执行任务" />
    </el-card>
  </div>
  <el-dialog
  v-model="partyDialogVisible"
  title="新增任务参与方"
  width="560px"
  destroy-on-close
>
  <el-form
    ref="partyFormRef"
    :model="partyForm"
    :rules="partyRules"
    label-width="120px"
  >
    <el-form-item label="机构ID" prop="agency_id">
      <el-input-number v-model="partyForm.agency_id" :min="1" style="width: 100%" />
    </el-form-item>

    <el-form-item label="节点ID" prop="node_id">
      <el-input-number v-model="partyForm.node_id" :min="1" style="width: 100%" />
    </el-form-item>

    <el-form-item label="数据资源ID" prop="dataset_id">
      <el-input-number v-model="partyForm.dataset_id" :min="1" style="width: 100%" />
    </el-form-item>

    <el-form-item label="参与角色">
      <el-select v-model="partyForm.party_role" style="width: 100%">
        <el-option label="数据提供方" value="data_provider" />
        <el-option label="结果接收方" value="result_receiver" />
        <el-option label="协调方" value="coordinator" />
      </el-select>
    </el-form-item>

    <el-form-item label="字段映射">
      <el-input
        v-model="fieldMappingText"
        type="textarea"
        :rows="6"
        placeholder='例如：{"patient_id":"patient_id","positive":"positive"}'
      />
    </el-form-item>
  </el-form>

  <template #footer>
    <el-button @click="partyDialogVisible = false">取消</el-button>
    <el-button type="primary" :loading="creatingParty" @click="handleCreateParty">
      保存
    </el-button>
  </template>
</el-dialog>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createTaskParty,
  getTaskDetail,
  getTaskParties,
  getTaskResult,
  runTask,
} from '@/api/task'

const route = useRoute()
const router = useRouter()

const taskId = route.params.id as string

const loading = ref(false)
const running = ref(false)

const taskDetail = ref<any>(null)
const partyList = ref<any[]>([])
const taskResult = ref<any>(null)

const partyDialogVisible = ref(false)
const creatingParty = ref(false)
const partyFormRef = ref<FormInstance>()

const fieldMappingText = ref('{\n  "patient_id": "patient_id",\n  "positive": "positive"\n}')

const partyForm = ref({
  agency_id: 1,
  node_id: 1,
  dataset_id: 1,
  party_role: 'data_provider',
  field_mapping_json: {},
})

const partyRules: FormRules = {
  agency_id: [{ required: true, message: '请输入机构ID', trigger: 'blur' }],
  node_id: [{ required: true, message: '请输入节点ID', trigger: 'blur' }],
  dataset_id: [{ required: true, message: '请输入数据资源ID', trigger: 'blur' }],
}

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

function normalizeList(payload: any) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.list)) return payload.list
  if (Array.isArray(payload?.records)) return payload.records
  return []
}

async function loadDetail() {
  loading.value = true
  try {
    const res = await getTaskDetail(taskId)
    taskDetail.value = unwrapResponse(res)
  } catch (error) {
    console.error(error)
    ElMessage.error('任务详情加载失败')
  } finally {
    loading.value = false
  }
}

async function loadParties() {
  try {
    const res = await getTaskParties(taskId)
    partyList.value = normalizeList(unwrapResponse(res))
  } catch (error) {
    console.warn('参与方接口暂不可用或暂无数据', error)
    partyList.value = []
  }
}

async function loadResult() {
  try {
    const res = await getTaskResult(taskId)
    taskResult.value = unwrapResponse(res)
  } catch (error) {
    console.warn('暂无统计结果', error)
    taskResult.value = null
  }
}

function openPartyDialog() {
  partyDialogVisible.value = true
  partyForm.value = {
    agency_id: 1,
    node_id: 1,
    dataset_id: 1,
    party_role: 'data_provider',
    field_mapping_json: {},
  }

  fieldMappingText.value = '{\n  "patient_id": "patient_id",\n  "positive": "positive"\n}'
}

async function handleCreateParty() {
  if (!partyFormRef.value) return

  await partyFormRef.value.validate(async (valid) => {
    if (!valid) return

    creatingParty.value = true

    try {
      let fieldMapping = {}

      if (fieldMappingText.value.trim()) {
        fieldMapping = JSON.parse(fieldMappingText.value)
      }

      await createTaskParty(taskId, {
        ...partyForm.value,
        field_mapping_json: fieldMapping,
      })

      ElMessage.success('参与方新增成功')
      partyDialogVisible.value = false
      await loadParties()
    } catch (error) {
      console.error(error)
      ElMessage.error('参与方新增失败，请检查字段映射 JSON 或后端请求体')
    } finally {
      creatingParty.value = false
    }
  })
}

async function handleRun() {
  if (!partyList.value.length) {
  ElMessage.warning('请先配置任务参与方，再执行联合统计任务')
  return
}
  try {
    await ElMessageBox.confirm(
      '确认执行当前联合统计任务吗？',
      '执行确认',
      {
        type: 'warning',
        confirmButtonText: '执行',
        cancelButtonText: '取消',
      },
    )

    running.value = true
    await runTask(taskId)

    ElMessage.success('任务执行成功')

    await loadDetail()
    await loadParties()
    await loadResult()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('任务执行失败')
    }
  } finally {
    running.value = false
  }
}

function goBack() {
  router.push('/tasks')
}

function formatJson(value: any) {
  if (!value) return '-'

  try {
    if (typeof value === 'string') {
      return JSON.stringify(JSON.parse(value), null, 2)
    }

    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
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

onMounted(async () => {
  await loadDetail()
  await loadParties()

  if (route.query.tab === 'result') {
    await loadResult()
  }
})
</script>

<style scoped>
.task-detail-page {
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

.section-card {
  margin-top: 16px;
}

.card-title {
  font-weight: 600;
  color: #1f2d3d;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.json-title {
  margin-top: 16px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #1f2d3d;
}

.json-view {
  padding: 16px;
  background: #0f172a;
  color: #e5e7eb;
  border-radius: 8px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
}
</style>