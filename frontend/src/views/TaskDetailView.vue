<template>
  <div class="task-detail-page">
    <div class="page-header">
      <div>
        <h2>任务详情</h2>
        <p>查看任务配置、执行状态和结果信息</p>
      </div>

      <div class="header-actions">
        <el-button @click="goBack">返回列表</el-button>
        <el-button
          type="success"
          :loading="running"
          :disabled="isFederatedLearningTask(taskDetail)"
          @click="handleRun"
        >
          {{ isFederatedLearningTask(taskDetail) ? '待开发' : '执行任务' }}
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

        <el-descriptions-item label="任务类型">
          <el-tag :type="getTaskTypeTagType(taskDetail)">
            {{ getTaskTypeText(taskDetail) }}
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
          <el-button
            type="primary"
            plain
            @click="openPartyDialog"
          >
            新增参与方
          </el-button>
        </div>
      </template>

      <el-table :data="partyList" border style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="agency_id" label="机构ID" width="120" />
        <el-table-column prop="node_id" label="节点ID" width="120" />
        <el-table-column prop="dataset_id" label="数据资源ID" width="130" />
        <el-table-column prop="party_role" label="参与角色" width="140" />

        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" min-width="170" />

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              @click="handleDeleteParty(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!partyList.length" description="暂无参与方数据" />
    </el-card>

    <el-alert
      v-if="isFederatedLearningTask(taskDetail)"
      class="section-card"
      title="联邦学习任务能力待接入"
      type="warning"
      description="当前页面已预留联邦学习任务入口，后续将在任务模型、算法配置、训练参数和执行框架确定后开放。"
      show-icon
      :closable="false"
    />

    <el-alert
      v-else
      class="section-card"
      title="当前任务类型：联合统计"
      type="success"
      description="当前任务继续使用已有联合统计流程，可配置参与方、执行任务并查看统计结果。"
      show-icon
      :closable="false"
    />

    <el-card
      v-if="!isFederatedLearningTask(taskDetail)"
      class="section-card"
      shadow="never"
    >


  <template #header>
    <div class="result-header">
      <div class="card-title">统计结果</div>
      <el-button type="primary" plain @click="loadResult">
        刷新结果
      </el-button>
    </div>
  </template>

  <template v-if="taskResult">
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">病例数</div>
        <div class="metric-value">
          {{ formatMetricNumber(resultMetrics.case_count) }}
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-label">去重人数</div>
        <div class="metric-value">
          {{ formatMetricNumber(resultMetrics.unique_patient_count) }}
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-label">阳性数</div>
        <div class="metric-value">
          {{ formatMetricNumber(resultMetrics.positive_count) }}
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-label">阳性率</div>
        <div class="metric-value">
          {{ formatRate(resultMetrics.positive_rate) }}
        </div>
      </div>
    </div>

    <el-descriptions class="result-desc" :column="2" border>
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

    <div class="json-title">原始结果 JSON</div>

    <pre class="json-view">{{ formatJson(taskResult.result_json || taskResult.metrics_json || taskResult) }}</pre>
  </template>

  <el-empty v-else description="暂无统计结果，请先执行任务" />
</el-card>
  </div>
<el-dialog
  v-if="!isFederatedLearningTask(taskDetail)"
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
<el-form-item label="参与机构" prop="agency_id">
  <el-select
    v-model="partyForm.agency_id"
    placeholder="请选择参与机构"
    filterable
    clearable
    style="width: 100%"
    :loading="resourceLoading"
    @change="handleAgencyChange"
  >
    <el-option
      v-for="item in agencyOptions"
      :key="item.id"
      :label="item.agency_name || item.name || item.agency_code || `机构${item.id}`"
      :value="item.id"
    />
  </el-select>
</el-form-item>

<el-form-item label="参与节点" prop="node_id">
  <el-select
    v-model="partyForm.node_id"
    placeholder="请选择参与节点"
    filterable
    clearable
    style="width: 100%"
    :loading="resourceLoading"
  >
    <el-option
      v-for="item in filteredNodeOptions"
      :key="item.id"
      :label="item.node_name || item.name || item.node_code || `节点${item.id}`"
      :value="item.id"
    />
  </el-select>
</el-form-item>

<el-form-item label="数据资源" prop="dataset_id">
  <el-select
    v-model="partyForm.dataset_id"
    placeholder="请选择本地数据资源"
    filterable
    clearable
    style="width: 100%"
    :loading="resourceLoading"
  >
    <el-option
      v-for="item in filteredDatasetOptions"
      :key="item.id"
      :label="item.dataset_name || item.name || item.dataset_code || `数据资源${item.id}`"
      :value="item.id"
    />
  </el-select>
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createTaskParty,
  deleteTaskParty,
  getTaskDetail,
  getTaskParties,
  getTaskResult,
  runTask,
} from '@/api/task'



import { getAgencyList } from '@/api/agency'
import { getNodeList } from '@/api/node'
import { getDatasetList } from '@/api/dataset'



const route = useRoute()
const router = useRouter()

type TaskType = 'statistic' | 'federated_learning'

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


// 下拉框
const resourceLoading = ref(false)

const agencyOptions = ref<any[]>([])
const nodeOptions = ref<any[]>([])
const datasetOptions = ref<any[]>([])

const filteredNodeOptions = computed(() => {
  if (!partyForm.value.agency_id) return nodeOptions.value
  return nodeOptions.value.filter((item) => item.agency_id === partyForm.value.agency_id)
})

const filteredDatasetOptions = computed(() => {
  if (!partyForm.value.agency_id) return datasetOptions.value
  return datasetOptions.value.filter((item) => item.agency_id === partyForm.value.agency_id)
})




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

async function openPartyDialog() {
  partyDialogVisible.value = true

  partyForm.value = {
    agency_id: null,
    node_id: null,
    dataset_id: null,
    party_role: 'data_provider',
    field_mapping_json: {},
  }

  fieldMappingText.value = '{\n  "patient_id": "patient_id",\n  "positive": "positive"\n}'

  await loadResourceOptions()
}

function handleAgencyChange() {
  partyForm.value.node_id = null
  partyForm.value.dataset_id = null
}

async function handleCreateParty() {
  if (!partyFormRef.value) return

  await partyFormRef.value.validate(async (valid) => {
    if (!valid) return

    if (!partyForm.value.agency_id || !partyForm.value.node_id || !partyForm.value.dataset_id) {
      ElMessage.warning('请选择参与机构、参与节点和数据资源')
      return
    }

    creatingParty.value = true

    try {
      let fieldMapping = {}

      if (fieldMappingText.value.trim()) {
        fieldMapping = JSON.parse(fieldMappingText.value)
      }

      await createTaskParty(taskId, {
        agency_id: partyForm.value.agency_id,
        node_id: partyForm.value.node_id,
        dataset_id: partyForm.value.dataset_id,
        party_role: partyForm.value.party_role,
        field_mapping_json: fieldMapping,
      })

      ElMessage.success('参与方新增成功')
      partyDialogVisible.value = false
      await loadParties()
    } catch (error) {
      console.error(error)
      ElMessage.error('参与方新增失败，请检查字段映射 JSON 或后端数据约束')
    } finally {
      creatingParty.value = false
    }
  })
}

async function handleRun() {
  if (isFederatedLearningTask(taskDetail.value)) {
    ElMessage.warning('联邦学习任务执行能力待开发')
    return
  }

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

function getTaskType(row: any): TaskType {
  const paramsJson = parseJsonValue(row?.params_json)
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

// 删除
async function loadResourceOptions() {
  resourceLoading.value = true

  try {
    const [agencyRes, nodeRes, datasetRes] = await Promise.all([
      getAgencyList({ page: 1, page_size: 100 }),
      getNodeList({ page: 1, page_size: 100 }),
      getDatasetList({ page: 1, page_size: 100 }),
    ])

    agencyOptions.value = normalizeList(unwrapResponse(agencyRes))
    nodeOptions.value = normalizeList(unwrapResponse(nodeRes))
    datasetOptions.value = normalizeList(unwrapResponse(datasetRes))
  } catch (error) {
    console.error(error)
    ElMessage.error('机构、节点或数据资源列表加载失败')
  } finally {
    resourceLoading.value = false
  }
}

async function handleDeleteParty(row: any) {
  try {
    await ElMessageBox.confirm(
      `确认删除该参与方吗？机构ID：${row.agency_id}，数据资源ID：${row.dataset_id}`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )

    await deleteTaskParty(taskId, row.id)

    ElMessage.success('参与方删除成功')

    await loadParties()
    await loadDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('参与方删除失败')
    }
  }
}


const resultMetrics = computed(() => {
  const resultJson = parseJsonValue(taskResult.value?.result_json)
  const metricsJson = parseJsonValue(taskResult.value?.metrics_json)

  const source = {
    ...metricsJson,
    ...resultJson,
  }

  return {
    case_count: source.case_count ?? source.metrics?.case_count ?? null,
    unique_patient_count:
      source.unique_patient_count ?? source.metrics?.unique_patient_count ?? null,
    positive_count: source.positive_count ?? source.metrics?.positive_count ?? null,
    positive_rate: source.positive_rate ?? source.metrics?.positive_rate ?? null,
  }
})

function parseJsonValue(value: any) {
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

function formatMetricNumber(value: any) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toLocaleString()
}

function formatRate(value: any) {
  if (value === null || value === undefined || value === '') return '-'

  const num = Number(value)

  if (Number.isNaN(num)) return '-'

  if (num <= 1) {
    return `${(num * 100).toFixed(2)}%`
  }

  return `${num.toFixed(2)}%`
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

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.metric-card {
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.metric-label {
  font-size: 14px;
  color: #7a8499;
  margin-bottom: 10px;
}

.metric-value {
  font-size: 26px;
  font-weight: 700;
  color: #1f2d3d;
}

.result-desc {
  margin-top: 16px;
}

@media (max-width: 1200px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}

</style>