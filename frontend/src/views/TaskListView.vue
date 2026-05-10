<template>
  <div class="task-page">
    <header class="page-header">
      <div class="title-area">
        <h1>任务调度中心</h1>
        <p>统一管理联合统计任务、联邦学习训练任务及结果存证</p>
      </div>

      <div class="header-actions">
        <el-button :icon="Refresh" @click="loadTasks">刷新态势</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新建任务</el-button>
      </div>
    </header>

    <main class="page-content">
      <el-card class="query-card" shadow="never">
        <el-form :inline="true" :model="queryForm" class="query-form">
          <el-form-item label="任务名称">
            <el-input
              v-model="queryForm.keyword"
              placeholder="请输入任务名称或编号"
              clearable
              style="width: 220px"
              @keyup.enter="loadTasks"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-form-item label="任务状态">
            <el-select v-model="queryForm.status" placeholder="全部状态" clearable style="width: 140px">
              <el-option label="已创建" value="created" />
              <el-option label="执行中" value="running" />
              <el-option label="执行成功" value="success" />
              <el-option label="执行失败" value="failed" />
            </el-select>
          </el-form-item>

          <el-form-item label="任务类型">
            <el-select v-model="queryForm.task_type" placeholder="全部类型" clearable style="width: 140px">
              <el-option v-for="item in TASK_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>

          <el-form-item label="任务场景">
            <el-select v-model="queryForm.scenario_code" placeholder="全部场景" clearable style="width: 240px">
              <el-option v-for="item in TASK_SCENARIO_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :icon="Search" @click="loadTasks">查询</el-button>
            <el-button :icon="RefreshLeft" @click="resetQuery">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <h3 class="section-title">任务执行大盘</h3>
      <el-card shadow="never" class="table-card">
        <el-table v-loading="loading" :data="filteredTaskList" border stripe style="width: 100%">
          <el-table-column prop="id" label="ID" width="70" align="center" />

          <el-table-column prop="task_code" label="任务编号 (Task Code)" min-width="240">
            <template #default="{ row }">
              <div class="hash-wrapper" title="点击复制编号" @click="copyText(row.task_code)">
                <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                <span class="hash-text">{{ row.task_code }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="task_name" label="任务名称" min-width="200" show-overflow-tooltip />

          <el-table-column label="任务类型" width="140" align="center">
            <template #default="{ row }">
              <el-tag :type="getTaskTypeTagType(row)" effect="plain">
                {{ getTaskTypeText(row) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="任务场景" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              {{ getTaskScenarioText(row) }}
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" effect="dark" size="small">
                {{ getStatusText(row.status).toUpperCase() }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="created_at" label="创建时间" width="170" />

          <el-table-column label="操作指令" width="260" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" :icon="View" @click="goDetail(row.id)">详情</el-button>

              <el-button
                link
                type="success"
                :icon="VideoPlay"
                :loading="runningTaskId === row.id"
                :disabled="!canRunTask(row)"
                @click="handleRun(row)"
              >
                {{ getRunButtonText(row) }}
              </el-button>

              <el-button
                link
                :type="row.status === 'success' ? 'warning' : 'info'"
                :icon="DataBoard"
                @click="goResult(row)"
              >
                {{ row.status === 'success' ? '查看结果' : '暂无结果' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            background
            layout="total, prev, pager, next, jumper"
            :total="total"
            :page-size="queryForm.page_size"
            v-model:current-page="queryForm.page"
            @current-change="loadTasks"
          />
        </div>
      </el-card>
    </main>

    <el-dialog v-model="createDialogVisible" title="构建协同计算任务" width="680px" destroy-on-close class="custom-dialog">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="120px" class="tech-form">
        <el-form-item label="任务编号" prop="task_code">
          <el-input v-model="createForm.task_code" placeholder="例如 FLU_TASK_20260504_001" class="mono-input" />
        </el-form-item>

        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="createForm.task_name" placeholder="例如 流感样病例联合统计任务" />
        </el-form-item>

        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="createForm.task_type" placeholder="请选择任务类型" style="width: 100%" @change="handleTaskTypeChange">
            <el-option v-for="item in TASK_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon> 已接入 Alice 18181 SecretFlow 联邦训练服务；支持真实联邦训练及结果链上存证。
          </div>
        </el-form-item>

        <el-form-item v-if="createForm.task_type === 'federated_learning'" label="任务场景" prop="scenario_code">
          <el-select v-model="createForm.scenario_code" placeholder="请选择任务场景" style="width: 100%">
            <el-option v-for="item in TASK_SCENARIO_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <div class="form-tip">
            <el-icon><Warning /></el-icon> 基于脱敏个案数据开展横向联邦学习，包含隐私求交溯源配置。
          </div>
        </el-form-item>

        <el-form-item v-if="createForm.task_type === 'statistic'" label="统计模板" prop="template_id">
          <el-select v-model="createForm.template_id" placeholder="请选择统计模板" filterable clearable style="width: 100%" :loading="templateLoading">
            <el-option v-for="item in templateOptions" :key="item.id" :label="item.template_name || item.name || item.template_code || `模板${item.id}`" :value="item.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="创建机构" prop="creator_agency_id">
          <el-select v-model="createForm.creator_agency_id" placeholder="请选择创建机构" filterable clearable style="width: 100%" :loading="agencyLoading">
            <el-option v-for="item in agencyOptions" :key="item.id" :label="item.agency_name || item.name || item.agency_code || `机构${item.id}`" :value="item.id" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="createForm.task_type === 'statistic'" label="统计时间范围">
          <el-date-picker v-model="statRange" type="datetimerange" start-placeholder="开始时间" end-placeholder="结束时间" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>

        <el-form-item v-if="createForm.task_type === 'federated_learning'" label="计算引擎配置">
          <div class="fl-terminal-box">
            <div class="terminal-header">
              <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
              <span class="terminal-title">bash - SecretFlow_Config</span>
            </div>
            <div class="terminal-body">
              <div><span class="keyword">Federated_Mode:</span> Horizontal Learning</div>
              <div><span class="keyword">Framework:</span> SecretFlow Core</div>
              <div><span class="keyword">Model_Type:</span> FLModel + Torch MLP Classifier</div>
              <div><span class="keyword">Agg_Strategy:</span> fed_avg_w</div>
              <div><span class="keyword">Agg_Method:</span> SparsePlainAggregator (Validation)</div>
              <div><span class="keyword">Data_Boundary:</span> Strictly Local (Returns only metrics & hashes)</div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入任务目标或描述..." />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消放弃</el-button>
        <el-button type="primary" :icon="Connection" :loading="creating" @click="handleCreate">
          初始化调度网络
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
// 引入所需的图标
import {
  Search, Refresh, RefreshLeft, Plus, View, VideoPlay, DataBoard,
  DocumentCopy, InfoFilled, Warning, Connection
} from '@element-plus/icons-vue'
import {
  createTask, getTaskList, getTaskResult, runTask, type CreateTaskPayload,
} from '@/api/task'
import {
  buildTaskParamsJson, isFederatedLearningTask, getTaskScenarioCodeFromRow as getTaskScenarioCode,
  getTaskScenarioTextFromRow as getTaskScenarioText, getTaskTypeFromRow as getTaskType,
  getTaskTypeTagTypeFromRow as getTaskTypeTagType, getTaskTypeTextFromRow as getTaskTypeText,
  TASK_SCENARIO_OPTIONS, TASK_TYPE_OPTIONS, type ScenarioCode, type TaskType,
} from '@/constants/taskScenario'

// --- 以下核心逻辑完全保留原有代码 ---
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

const queryForm = reactive({ page: 1, page_size: 10, keyword: '', status: '', task_type: '', scenario_code: '' })

const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const statRange = ref<string[]>([])

const createForm = reactive<CreateTaskPayload & { task_type: TaskType; scenario_code: ScenarioCode }>({
  task_code: '', task_name: '', task_type: 'statistic', scenario_code: 'infectious_spatiotemporal_prediction',
  template_id: null, creator_agency_id: null, stat_start_time: '', stat_end_time: '', description: '',
})

const createRules: FormRules = {
  task_code: [{ required: true, message: '请输入任务编号', trigger: 'blur' }],
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  scenario_code: [{ required: true, message: '请选择任务场景', trigger: 'change' }],
  creator_agency_id: [{ required: true, message: '请选择创建机构', trigger: 'change' }],
}

// 辅助方法：复制文本
async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('任务编号已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

function unwrapResponse(res: any) { return res?.data?.data ?? res?.data ?? res }

function normalizeList(payload: any) {
  if (Array.isArray(payload)) return { list: payload, total: payload.length }
  if (Array.isArray(payload?.items)) return { list: payload.items, total: payload.total ?? payload.items.length }
  if (Array.isArray(payload?.list)) return { list: payload.list, total: payload.total ?? payload.list.length }
  if (Array.isArray(payload?.records)) return { list: payload.records, total: payload.total ?? payload.records.length }
  return { list: [], total: 0 }
}

const filteredTaskList = computed(() => {
  return taskList.value.filter((item) => {
    const matchedType = !queryForm.task_type || getTaskType(item) === queryForm.task_type
    const matchedScenario = !queryForm.scenario_code || getTaskScenarioCode(item) === queryForm.scenario_code
    return matchedType && matchedScenario
  })
})

async function loadAgencyOptions() {
  agencyLoading.value = true
  try {
    const res = await getAgencyList({ page: 1, page_size: 100 })
    agencyOptions.value = normalizeList(unwrapResponse(res)).list
  } catch (error) { ElMessage.error('机构列表加载失败') } finally { agencyLoading.value = false }
}

async function loadTemplateOptions() {
  templateLoading.value = true
  try {
    const res = await getStatTemplateList({ page: 1, page_size: 100 })
    templateOptions.value = normalizeList(unwrapResponse(res)).list
  } catch (error) { ElMessage.error('统计模板列表加载失败') } finally { templateLoading.value = false }
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await getTaskList({
      page: queryForm.page, page_size: queryForm.page_size,
      keyword: queryForm.keyword || undefined, status: queryForm.status || undefined,
    })
    const normalized = normalizeList(unwrapResponse(res))
    taskList.value = normalized.list
    total.value = normalized.total
  } catch (error) { ElMessage.error('任务列表加载失败') } finally { loading.value = false }
}

function resetQuery() {
  queryForm.page = 1; queryForm.keyword = ''; queryForm.status = '';
  queryForm.task_type = ''; queryForm.scenario_code = '';
  loadTasks()
}

async function openCreateDialog() {
  createDialogVisible.value = true
  createForm.task_code = `FLU_TASK_${Date.now()}`
  createForm.task_name = ''
  createForm.task_type = 'statistic'
  createForm.scenario_code = 'infectious_spatiotemporal_prediction'
  createForm.template_id = null
  createForm.creator_agency_id = null
  createForm.description = ''
  statRange.value = []
  await Promise.all([loadAgencyOptions(), loadTemplateOptions()])
}

function handleTaskTypeChange() {
  if (createForm.task_type === 'federated_learning') {
    createForm.scenario_code = 'infectious_spatiotemporal_prediction'
    createForm.template_id = null
    statRange.value = []
    if (!createForm.task_name) createForm.task_name = 'T2 跨区县传染病时空预测与疫情溯源任务'
    if (createForm.task_code.startsWith('FLU_TASK_')) createForm.task_code = `FED_TASK_${Date.now()}`
  }
  if (createForm.task_type === 'statistic') {
    if (createForm.task_code.startsWith('FED_TASK_')) createForm.task_code = `FLU_TASK_${Date.now()}`
  }
}

function buildRealFederatedLearningParamsJson(scenarioCode: ScenarioCode) {
  return {
    task_type: 'federated_learning', framework: 'secretflow', model_type: 'FLModel_torch_mlp_binary_classifier',
    federated_mode: 'horizontal', train_mode: 'horizontal', partition_type: 'horizontal',
    strategy: 'fed_avg_w', aggregator: 'SparsePlainAggregator', algorithm_type: 'prediction',
    scenario_code: scenarioCode, scenario_name: '跨区县传染病时空预测与疫情溯源',
    train_config: { epochs: 5, batch_size: 32, learning_rate: 0.01 },
    secretflow_fl: { alice_csv: '/data/alice_flu_fl_train.csv', bob_csv: '/data/bob_flu_fl_train.csv' },
    dataset_config: {
      id_column: 'case_id_hash', main_table: 'IDSR_INDIVIDUAL_DIS', label_column: 'risk_label',
      feature_columns: ['disease_code', 'onset_date', 'diagnosis_date', 'spatial_grid_id', 'age_group', 'gender', 'occupation_code'],
    },
    trace_config: { enabled: true, trace_table: 'SPATIOTEMPORAL_TRACE', trace_method: 'private_intersection', intersection_field: 'spatial_grid_14d' },
    privacy_config: { raw_data_export: false, blockchain_audit: true, aggregator: 'SparsePlainAggregator', note: '当前为验证版' },
  }
}

async function handleCreate() {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (createForm.task_type === 'statistic' && !createForm.template_id) { ElMessage.warning('请选择统计模板'); return }
    if (createForm.task_type === 'federated_learning' && !createForm.scenario_code) { ElMessage.warning('请选择联邦学习任务场景'); return }
    if (!createForm.creator_agency_id) { ElMessage.warning('请选择创建机构'); return }

    creating.value = true
    try {
      const isFederated = createForm.task_type === 'federated_learning'
      const payload: CreateTaskPayload = {
        task_code: createForm.task_code, task_name: createForm.task_name,
        template_id: isFederated ? null : createForm.template_id, creator_agency_id: createForm.creator_agency_id,
        description: createForm.description || undefined,
        stat_start_time: isFederated ? undefined : statRange.value?.[0] || undefined,
        stat_end_time: isFederated ? undefined : statRange.value?.[1] || undefined,
        params_json: isFederated ? buildRealFederatedLearningParamsJson(createForm.scenario_code) : buildTaskParamsJson(createForm.task_type, undefined),
      }
      await createTask(payload)
      ElMessage.success('任务初始化调度成功')
      createDialogVisible.value = false
      await loadTasks()
    } catch (error) { ElMessage.error('调度失败，请检查参数') } finally { creating.value = false }
  })
}

function goDetail(taskId: number | string) { router.push(`/tasks/${taskId}`) }

async function handleRun(row: any) {
  const isFlTask = isFederatedLearningTask(row)
  if (row.status === 'success') { ElMessage.info('已执行完毕'); return }
  if (row.status === 'running') { ElMessage.warning('执行中，请等待'); return }

  try {
    await ElMessageBox.confirm(`确认触发协同计算指令「${row.task_name || row.task_code}」吗？`, '调度确认', {
      type: 'warning', confirmButtonText: row.status === 'failed' ? '重启指令' : '执行', cancelButtonText: '取消',
    })
    runningTaskId.value = row.id
    await runTask(row.id)
    ElMessage.success('计算节点已被唤醒，任务下发成功')
    await loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('节点无响应或下发失败')
  } finally { runningTaskId.value = null }
}

async function goResult(row: any) {
  if (row.status !== 'success') { ElMessage.warning('结果尚未生成'); return }
  try {
    await getTaskResult(row.id)
    router.push(`/tasks/${row.id}?tab=result`)
  } catch (error) { ElMessage.warning('结果提取失败') }
}

function getStatusText(status: string) {
  const map: Record<string, string> = { created: '已编排', pending: '等待中', running: '计算中', success: '已完成', failed: '中断', canceled: '已取消' }
  return map[status] || status || '-'
}

function getStatusType(status: string) {
  const map: Record<string, string> = { created: 'info', pending: 'info', running: 'warning', success: 'success', failed: 'danger', canceled: 'info' }
  return map[status] || 'info'
}

function canRunTask(row: any) { return ['created', 'pending', 'failed'].includes(row.status) }
function getRunButtonText(row: any) {
  const isFlTask = isFederatedLearningTask(row)
  if (runningTaskId.value === row.id) return '计算中'
  if (row.status === 'success') return isFlTask ? '已收敛' : '已归档'
  if (row.status === 'running') return '计算中'
  if (row.status === 'failed') return '重启节点'
  return isFlTask ? '启动联邦' : '触发计算'
}

onMounted(() => { loadTasks() })
</script>

<style scoped>
/* 基础页面布局 (与 Dashboard 一致) */
.task-page {
  min-height: 100vh;
  background: #f0f2f5;
}

.page-header {
  height: 72px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-area h1 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
  font-weight: 600;
}

.title-area p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.page-content {
  padding: 24px;
}

/* 模块标题规范 */
.section-title {
  margin: 20px 0 16px 0;
  font-size: 16px;
  color: #374151;
  font-weight: 600;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

/* 搜索表单卡片 */
.query-card {
  margin-bottom: 24px;
  border-radius: 8px;
  border: none;
}
.query-form .el-form-item {
  margin-bottom: 16px;
  margin-right: 24px;
}

/* 表格卡片 */
.table-card {
  border-radius: 8px;
  border: none;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* 极客美学：等宽编号样式 (Hash Wrapper) */
.hash-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
}
.hash-wrapper:hover {
  background: #e5e7eb;
  border-color: #d1d5db;
}
.hash-icon {
  color: #409eff;
  font-size: 14px;
}
.hash-text {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  color: #374151;
  letter-spacing: 0.5px;
}

/* 表单辅助说明文字 */
.form-tip {
  margin-top: 6px;
  color: #8c96a8;
  font-size: 12px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 科技风：联邦学习配置框 (类似 Terminal) */
.fl-terminal-box {
  width: 100%;
  border-radius: 8px;
  background: #1e1e1e;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.terminal-header {
  background: #2d2d2d;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid #404040;
}

.terminal-header .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }

.terminal-title {
  margin-left: 10px;
  color: #a0a0a0;
  font-family: 'Consolas', monospace;
  font-size: 12px;
}

.terminal-body {
  padding: 12px 16px;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.8;
}

.terminal-body .keyword {
  color: #569cd6; /* VS Code 蓝 */
  font-weight: bold;
}

.mono-input :deep(.el-input__inner) {
  font-family: 'Consolas', 'Monaco', monospace;
}
</style>