<template>
  <div class="task-detail-page">
    <header class="page-header">
      <div class="title-area">
        <h1>任务协同与审计详情</h1>
        <p>查看计算任务的编排配置、多方调度状态及区块链存证结果</p>
      </div>

      <div class="header-actions">
        <el-button :icon="Back" @click="goBack">返回大盘</el-button>
        <el-button
          type="success"
          :icon="VideoPlay"
          :loading="running"
          :disabled="running"
          @click="handleRun"
        >
          {{ isFederatedLearningTask(taskDetail) ? '下发联邦计算指令' : '触发协同统计' }}
        </el-button>
      </div>
    </header>

    <main class="page-content">
      <h3 class="section-title">基础调度信息</h3>
      <el-card v-loading="loading" shadow="never" class="info-card">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务编号 (Task Code)">
            <div class="hash-wrapper" title="点击复制" @click="copyText(taskDetail?.task_code)">
              <el-icon class="hash-icon"><DocumentCopy /></el-icon>
              <span class="hash-text">{{ taskDetail?.task_code || '-' }}</span>
            </div>
          </el-descriptions-item>

          <el-descriptions-item label="任务状态">
            <el-tag :type="getStatusType(taskDetail?.status)" effect="dark">
              {{ getStatusText(taskDetail?.status).toUpperCase() }}
            </el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="任务类型">
            <el-tag :type="getTaskTypeTagType(taskDetail)" effect="plain">
              {{ getTaskTypeText(taskDetail) }}
            </el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="任务名称">
            <strong>{{ taskDetail?.task_name || '-' }}</strong>
          </el-descriptions-item>

          <el-descriptions-item label="系统 ID 标识">
            <span class="mono-text">TaskID: {{ taskDetail?.id || '-' }} | TemplateID: {{ taskDetail?.template_id || '-' }} | AgencyID: {{ taskDetail?.creator_agency_id || '-' }}</span>
          </el-descriptions-item>

          <el-descriptions-item label="时间周期">
            {{ taskDetail?.created_at || '-' }} (创建) / {{ taskDetail?.updated_at || '-' }} (更新)
          </el-descriptions-item>

          <el-descriptions-item label="任务描述" :span="2">
            <span style="color: #64748b;">{{ taskDetail?.description || '暂无描述' }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <template v-if="isFederatedLearningTask(taskDetail)">
        <h3 class="section-title">联邦计算引擎配置</h3>
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="result-header">
              <span class="card-title"><el-icon><Cpu /></el-icon> T2 SecretFlow 核心配置</span>
              <el-tag type="warning" effect="dark">真实计算网络已接入</el-tag>
            </div>
          </template>

          <div class="fl-section-grid">
            <div class="fl-info-panel">
              <div class="fl-info-title"><el-icon><DataBoard /></el-icon> 业务目标</div>
              <div class="fl-info-text">
                {{ taskParams.scenario_name || '跨区县传染病时空预测与疫情溯源' }}。在不汇聚原始数据的前提下，联合多个节点训练风险预测模型，输出全局准确率及损失值。
              </div>
            </div>
            <div class="fl-info-panel dark-panel">
              <div class="fl-info-title"><el-icon><Lock /></el-icon> 安全边界约束</div>
              <div class="fl-info-text">
                原始数据不出本地节点。系统仅接收训练指标、参与方摘要、结果哈希和链上存证凭证；当前聚合方式为 SparsePlainAggregator 验证版。
              </div>
            </div>
          </div>

          <el-descriptions :column="3" border class="mt-4">
            <el-descriptions-item label="联邦模式">{{ getFederatedModeText(taskParams.federated_mode) }}</el-descriptions-item>
            <el-descriptions-item label="算法类型">{{ getAlgorithmTypeText(taskParams.algorithm_type) }}</el-descriptions-item>
            <el-descriptions-item label="执行框架">{{ formatFramework(effectiveFlFramework) }}</el-descriptions-item>
            <el-descriptions-item label="模型网络" :span="2"><el-tag type="info">{{ effectiveFlModelTypeText }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="聚合策略">{{ effectiveFlAggregator }}</el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">核心训练超参</el-divider>
          <div class="config-metric-grid">
            <div class="config-metric-card"><div class="config-metric-label">Epochs (轮次)</div><div class="config-metric-value">{{ trainConfig.epochs ?? 5 }}</div></div>
            <div class="config-metric-card"><div class="config-metric-label">Batch Size (批大小)</div><div class="config-metric-value">{{ trainConfig.batch_size ?? 32 }}</div></div>
            <div class="config-metric-card"><div class="config-metric-label">Learning Rate (学习率)</div><div class="config-metric-value">{{ trainConfig.learning_rate ?? 0.01 }}</div></div>
          </div>
        </el-card>
      </template>

      <h3 class="section-title">参与方拓扑网络</h3>
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="result-header">
            <span class="card-title"><el-icon><Connection /></el-icon> 当前在线计算节点</span>
            <el-button type="primary" :icon="Plus" @click="openPartyDialog">
              {{ isFederatedLearningTask(taskDetail) ? '新增训练节点' : '新增参与方' }}
            </el-button>
          </div>
        </template>

        <el-table :data="partyList" border stripe style="width: 100%">
          <el-table-column prop="agency_id" label="机构 ID" width="90" align="center" />
          <el-table-column prop="node_id" label="节点标识" width="140">
             <template #default="{ row }">
              <span class="mono-text" style="color: #409eff;">Node_{{ row.node_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="party_role" label="授权角色" width="200">
            <template #default="{ row }">
              <template v-if="row.party_role && row.party_role.includes(',')">
                <el-tag v-for="role in row.party_role.split(',')" :key="role" :type="role === 'coordinator' ? 'danger' : 'success'" effect="plain" style="margin-right: 4px;">
                  {{ getPartyRoleText(role) }}
                </el-tag>
              </template>
              <el-tag v-else :type="row.party_role === 'coordinator' ? 'danger' : 'success'" effect="plain">
                {{ getPartyRoleText(row.party_role) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column v-if="isFederatedLearningTask(taskDetail)" label="本地数据源映射" min-width="240">
            <template #default="{ row }">
              <div class="text-sm">表: <strong>{{ getPartyLocalTable(row) }}</strong></div>
              <div class="text-xs text-gray">{{ getPartySampleDesc(row) }}</div>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="节点状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column label="节点操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="danger" :icon="Delete" @click="handleDeleteParty(row)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <h3 class="section-title">执行与结果入口</h3>
      <el-card class="section-card" shadow="never">
        <div class="dispatch-entry">
          <div>
            <div class="dispatch-title">当前页面仅展示任务配置与参与方拓扑</div>
            <div class="dispatch-desc">
              点击右上角“下发联邦计算指令”后，将进入结果页面；结果页面会先展示联邦训练过程动画，训练结束后再展示训练指标、结果哈希和链上存证信息。
            </div>
          </div>
          <el-button type="success" :icon="VideoPlay" @click="handleRun">
            {{ isFederatedLearningTask(taskDetail) ? '下发联邦计算指令' : '下发协同统计指令' }}
          </el-button>
        </div>
      </el-card>
    </main>

    <el-dialog v-model="partyDialogVisible" :title="isFederatedLearningTask(taskDetail) ? '新增训练节点' : '新增协同参与方'" width="680px" destroy-on-close>
      <el-form ref="partyFormRef" :model="partyForm" :rules="partyRules" label-width="120px">
        <el-form-item label="参与机构" prop="agency_id">
          <el-select v-model="partyForm.agency_id" filterable clearable style="width: 100%" :loading="resourceLoading" @change="handleAgencyChange">
            <el-option v-for="item in agencyOptions" :key="item.id" :label="item.agency_name || item.name || item.agency_code || `机构${item.id}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="参与节点" prop="node_id">
          <el-select v-model="partyForm.node_id" filterable clearable style="width: 100%" :loading="resourceLoading" @change="handleNodeChange">
            <el-option v-for="item in filteredNodeOptions" :key="item.id" :label="item.node_name || item.name || item.node_code || `节点${item.id}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据资源">
          <el-select v-model="partyForm.dataset_name" filterable clearable placeholder="请选择数据资源" style="width: 100%" :loading="resourceLoading">
            <el-option v-for="item in filteredDatasetOptions" :key="item.dataset_id" :label="item.dataset_name" :value="item.dataset_name" />
          </el-select>
        </el-form-item>
        <el-form-item label="参与角色">
          <el-select v-model="partyForm.party_roles" multiple collapse-tags collapse-tags-tooltip placeholder="请选择参与角色，可多选" style="width: 100%">
            <el-option v-for="item in partyRoleOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="isFederatedLearningTask(taskDetail) ? '训练字段映射' : '字段映射'">
          <el-input v-model="fieldMappingText" type="textarea" :rows="8" class="mono-input" placeholder='{"case_id_hash":"case_id_hash"}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="partyDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingParty" @click="handleCreateParty">保存节点</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
// 统一引入极客风图标
import {
  Back, VideoPlay, Refresh, Plus, DocumentCopy, Cpu, Lock,
  Connection, Link, DataBoard, DataLine, PieChart, Monitor, Check, Delete
} from '@element-plus/icons-vue'

import {
  anchorTaskResult, createTaskParty, deleteTaskParty, getTaskDetail,
  getTaskParties, getTaskResult, runTask,
} from '@/api/task'
import { getChainRecordList } from '@/api/chainRecord'
import { getAgencyList } from '@/api/agency'
import { getNodeList } from '@/api/node'
import { getDatasetList } from '@/api/dataset'
import { getGroupDatasets } from '@/api/group'
import {
  buildDefaultFieldMappingText, buildDefaultPartyRole, getAlgorithmTypeText,
  getFederatedModeText, getFlDatasetFieldRows, getFlProcessSteps,
  getModelTypeText, getPartyFieldCount, getPartyLocalTable,
  getPartySampleDesc, getTaskTypeTagTypeFromRow as getTaskTypeTagType,
  getTaskTypeTextFromRow as getTaskTypeText, isFederatedLearningTask, parseJsonValue,
} from '@/constants/taskScenario'

import FederatedAnimation from '@/components/FederatedAnimation.vue'

// --- 基础业务逻辑与状态管理保持不变 ---
const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const loading = ref(false)
const running = ref(false)
const anchoring = ref(false)
const taskDetail = ref<any>(null)
const partyList = ref<any[]>([])
const taskResult = ref<any>(null)
const chainAnchorResult = ref<any>(null)

const partyDialogVisible = ref(false)
const creatingParty = ref(false)
const partyFormRef = ref<FormInstance>()
const fieldMappingText = ref(buildDefaultFieldMappingText(taskDetail.value))
const partyForm = ref({ agency_id: null as number | null, node_id: null as number | null, dataset_name: null as string | null, party_roles: [] as string[], field_mapping_json: {} })

const statisticPartyRoleOptions = [{ label: '数据提供方', value: 'data_provider' }, { label: '结果接收方', value: 'result_receiver' }, { label: '协调方', value: 'coordinator' }]
const federatedPartyRoleOptions = [{ label: '训练方', value: 'training_client' }, { label: '协调方', value: 'coordinator' }, { label: '评估方', value: 'evaluator' }]
const partyRoleOptions = computed(() => (isFederatedLearningTask(taskDetail.value) ? federatedPartyRoleOptions : statisticPartyRoleOptions))

const partyRules: FormRules = {
  agency_id: [{ required: true, message: '请选择参与机构', trigger: 'change' }],
  node_id: [{ required: true, message: '请选择参与节点', trigger: 'change' }],
}

const resourceLoading = ref(false)
const agencyOptions = ref<any[]>([])
const nodeOptions = ref<any[]>([])
const datasetOptions = ref<any[]>([])
const filteredNodeOptions = computed(() => (!partyForm.value.agency_id ? nodeOptions.value : nodeOptions.value.filter((item) => item.agency_id === partyForm.value.agency_id)))
const filteredDatasetOptions = computed(() => {
  if (!partyForm.value.agency_id) return datasetOptions.value
  return datasetOptions.value.filter((item) => {
    if (item.agency_id !== partyForm.value.agency_id) return false
    if (partyForm.value.node_id && item.node_id && item.node_id !== partyForm.value.node_id) return false
    return true
  })
})

// 剪贴板复制工具
async function copyText(text: string) {
  if (!text || text === '-') return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

function unwrapResponse(res: any) { return res?.data?.data ?? res?.data ?? res }
function normalizeList(payload: any) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.list)) return payload.list
  if (Array.isArray(payload?.records)) return payload.records
  return []
}

async function loadDetail() {
  loading.value = true
  try { taskDetail.value = unwrapResponse(await getTaskDetail(taskId)) }
  catch (error) { ElMessage.error('任务详情加载失败') }
  finally { loading.value = false }
}

async function loadParties() {
  try { partyList.value = normalizeList(unwrapResponse(await getTaskParties(taskId))) }
  catch (error) { partyList.value = [] }
}

async function loadResult() {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
    await loadChainRecordForCurrentResult()
  } catch (error) {
    taskResult.value = null; chainAnchorResult.value = null
  }
}

async function loadChainRecordForCurrentResult() {
  if (!taskResult.value?.id) { chainAnchorResult.value = null; return }
  try {
    const data = unwrapResponse(await getChainRecordList({ page: 1, page_size: 1, biz_type: 'task_result', biz_id: String(taskResult.value.id), status: 'success' })) || {}
    const record = Array.isArray(data.items) ? data.items[0] : null
    chainAnchorResult.value = record ? { anchored: true, duplicated: true, message: '当前任务结果已完成 FISCO BCOS 链上存证', chain_record: record } : null
  } catch (error) { console.warn('存证记录加载失败', error) }
}

function sleep(ms: number) { return new Promise((resolve) => window.setTimeout(resolve, ms)) }
function isRequestTimeoutOrNetworkError(error: any) {
  const c = String(error?.code || ''); const m = String(error?.message || ''); const s = error?.response?.status;
  return c === 'ECONNABORTED' || c === 'ERR_NETWORK' || s === 504 || m.includes('timeout') || m.includes('Network') || m.includes('网络')
}

async function refreshRuntimeState() {
  await loadDetail(); await loadParties(); await loadResult();
  return taskDetail.value?.status === 'success' || taskResult.value?.status === 'success' || !!taskResult.value?.result_hash
}

async function recoverRunSuccessAfterRequestError(isFlTask: boolean) {
  for (let i = 0; i < 15; i += 1) {
    await sleep(i === 0 ? 1000 : 5000)
    if (await refreshRuntimeState()) { ElMessage.success(isFlTask ? '联邦训练已完成' : '任务已完成'); return true }
  }
  return false
}

async function openPartyDialog() {
  partyDialogVisible.value = true
  partyForm.value = { agency_id: null, node_id: null, dataset_name: null, party_roles: [], field_mapping_json: {} }
  fieldMappingText.value = buildDefaultFieldMappingText(taskDetail.value)
  await loadResourceOptions()
}

function handleAgencyChange() { partyForm.value.node_id = null; partyForm.value.dataset_name = null }
function handleNodeChange() { partyForm.value.dataset_name = null }

async function handleCreateParty() {
  if (!partyFormRef.value) return
  await partyFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (!partyForm.value.agency_id || !partyForm.value.node_id) { ElMessage.warning('请选择参与机构和参与节点'); return }
    if (!partyForm.value.party_roles || partyForm.value.party_roles.length === 0) { ElMessage.warning('请至少选择一个参与角色'); return }
    
    const hasDataProvider = partyForm.value.party_roles.includes('data_provider')
    if (hasDataProvider && !partyForm.value.dataset_name) { ElMessage.warning('数据提供方必须选择数据资源'); return }
    
    creatingParty.value = true
    try {
      let fm = {}; if (fieldMappingText.value.trim()) fm = JSON.parse(fieldMappingText.value);
      await createTaskParty(taskId, { 
        agency_id: partyForm.value.agency_id,
        node_id: partyForm.value.node_id,
        data_resource_name: partyForm.value.dataset_name,
        party_role: partyForm.value.party_roles.join(','),
        field_mapping_json: fm 
      })
      ElMessage.success('节点挂载成功'); partyDialogVisible.value = false; await loadParties();
    } catch (error) { ElMessage.error('节点挂载失败，请检查配置') }
    finally { creatingParty.value = false }
  })
}

async function handleRun() {
  if (!taskDetail.value) return
  if (!partyList.value.length) {
    ElMessage.warning('请先配置计算拓扑节点')
    return
  }

  const isFlTask = isFederatedLearningTask(taskDetail.value)
  const confirmText = isFlTask
    ? '确认下发联邦计算指令并进入训练结果页面吗？'
    : '确认下发协同统计指令并进入结果页面吗？'

  try {
    await ElMessageBox.confirm(confirmText, '下发确认', {
      type: 'warning',
      confirmButtonText: '下发并进入结果页',
      cancelButtonText: '取消',
    })

    router.push({
      name: 'TaskResult',
      params: { id: taskId },
      query: { autoRun: '1' },
    })
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('指令下发入口跳转失败')
  }
}

async function handleAnchorTaskResult() {
  if (!taskDetail.value || taskDetail.value.status !== 'success') { ElMessage.warning('任务未就绪'); return }
  if (!taskResult.value) { ElMessage.warning('无可用计算哈希'); return }
  try {
    await ElMessageBox.confirm('确认触发智能合约，将结算数据签发至 FISCO BCOS 联盟链？', '上链确认', { type: 'warning', confirmButtonText: '确认上链', cancelButtonText: '取消' })
    anchoring.value = true
    const data = unwrapResponse(await anchorTaskResult(taskId))
    chainAnchorResult.value = data
    if (data?.duplicated) ElMessage.info(data.message || '记录已存在')
    else ElMessage.success(data?.message || '智能合约执行完毕，数据已确权')
    await loadChainRecordForCurrentResult()
  } catch (error: any) { if (error !== 'cancel') ElMessage.error('合约调用超时或失败') }
  finally { anchoring.value = false }
}

function goBack() { router.push('/tasks') }

function formatJson(value: any) {
  if (!value) return '-'
  try { return typeof value === 'string' ? JSON.stringify(JSON.parse(value), null, 2) : JSON.stringify(value, null, 2) }
  catch { return String(value) }
}

const taskParams = computed(() => parseJsonValue(taskDetail.value?.params_json))
const datasetConfig = computed(() => taskParams.value?.dataset_config || {})
const trainConfig = computed(() => taskParams.value?.train_config || {})
const privacyConfig = computed(() => taskParams.value?.privacy_config || {})
const traceConfig = computed(() => taskParams.value?.trace_config || {})
const flDatasetFieldRows = computed(() => getFlDatasetFieldRows(taskParams.value))
const flProcessSteps = computed(() => getFlProcessSteps(taskParams.value))

function getPartyRoleText(value: string) {
  const map: Record<string, string> = { data_provider: '数据提供方', result_receiver: '结果接收方', coordinator: '总控协调节点', training_client: '本地计算节点', evaluator: '评估验证节点' }
  return map[value] || value || '-'
}

function getStatusText(status: string) {
  const map: Record<string, string> = { created: '已编排', pending: '调度中', running: '计算中', success: '执行成功', failed: '执行失败' }
  return map[status] || status || '-'
}

function getStatusType(status: string) {
  const map: Record<string, string> = { created: 'info', pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function formatChainType(type: string) { return type === 'fisco_bcos' ? 'FISCO BCOS' : type === 'mock_fisco_bcos' ? 'Mock FISCO BCOS' : type || '-' }
function formatFramework(value: string | null | undefined) { return value === 'mock' ? '历史 Mock 配置' : value === 'flower' ? 'Flower' : value === 'secretflow' ? 'SecretFlow Core' : value || '-' }

async function loadResourceOptions() {
  resourceLoading.value = true
  try {
    const [agencyRes, nodeRes] = await Promise.all([getAgencyList({ page: 1, page_size: 100 }), getNodeList({ page: 1, page_size: 100 })])
    agencyOptions.value = normalizeList(unwrapResponse(agencyRes))
    nodeOptions.value = normalizeList(unwrapResponse(nodeRes))
    
    if (taskDetail.value?.group_id) {
      const datasetRes = await getGroupDatasets(taskDetail.value.group_id)
      const data = unwrapResponse(datasetRes)
      datasetOptions.value = Array.isArray(data) ? data : []
    } else {
      datasetOptions.value = []
    }
  } catch (error) { ElMessage.error('基础资源池加载失败') } finally { resourceLoading.value = false }
}

async function handleDeleteParty(row: any) {
  try {
    await ElMessageBox.confirm('踢出该计算节点将影响协同拓扑，确认？', '断开确认', { type: 'danger', confirmButtonText: '强制断开', cancelButtonText: '取消' })
    await deleteTaskParty(taskId, row.id)
    ElMessage.success('节点已安全剥离'); await loadParties(); await loadDetail();
  } catch (error: any) { if (error !== 'cancel') ElMessage.error('节点剥离失败') }
}

const resultMetrics = computed(() => {
  const r = parseJsonValue(taskResult.value?.result_json); const m = parseJsonValue(taskResult.value?.metrics_json); const s = { ...m, ...r };
  return { case_count: s.case_count ?? s.metrics?.case_count ?? null, unique_patient_count: s.unique_patient_count ?? s.metrics?.unique_patient_count ?? null, positive_count: s.positive_count ?? s.metrics?.positive_count ?? null, positive_rate: s.positive_rate ?? s.metrics?.positive_rate ?? null }
})

const federatedResultJson = computed(() => parseJsonValue(taskResult.value?.result_json))
const federatedMetricsJson = computed(() => parseJsonValue(taskResult.value?.metrics_json))

const federatedSummary = computed(() => {
  const r = federatedResultJson.value || {}; const m = federatedMetricsJson.value || {}; const s = r.summary || {};
  return { final_accuracy: s.final_accuracy ?? m.final_accuracy ?? r.metrics?.accuracy, final_auc: s.final_auc ?? m.final_auc ?? r.metrics?.auc, final_precision: s.final_precision ?? m.final_precision ?? r.metrics?.precision, final_recall: s.final_recall ?? m.final_recall ?? r.metrics?.recall, final_f1: s.final_f1 ?? m.final_f1 ?? r.metrics?.f1, round_count: s.round_count ?? m.round_count ?? r.training_params?.epochs, participant_count: s.participant_count ?? m.participant_count ?? r.participants?.length, sample_count: s.sample_count ?? m.sample_count ?? r.metrics?.sample_count, privacy_mode: s.privacy_mode ?? m.privacy_mode ?? r.aggregator }
})

const effectiveFlFramework = computed(() => federatedResultJson.value?.framework || taskParams.value?.framework || 'secretflow')
const effectiveFlModelType = computed(() => federatedResultJson.value?.model_type || taskParams.value?.model_type || 'FLModel_torch_mlp_binary_classifier')
const effectiveFlModelTypeText = computed(() => effectiveFlModelType.value === 'FLModel_torch_mlp_binary_classifier' ? 'FLModel + Torch MLP 二分类模型' : getModelTypeText(effectiveFlModelType.value))
const effectiveFlAggregator = computed(() => federatedResultJson.value?.aggregator || federatedMetricsJson.value?.aggregator || 'SparsePlainAggregator')
const hasSuccessfulChainAnchor = computed(() => chainAnchorResult.value?.chain_record?.status === 'success')
const anchorButtonText = computed(() => hasSuccessfulChainAnchor.value ? '链上确权完毕' : '签发至区块链')

function formatMetricNumber(value: any) { return (value == null || value === '') ? '-' : Number(value).toLocaleString() }
function formatRate(value: any) { const n = Number(value); return isNaN(n) ? '-' : `${(n <= 1 ? n * 100 : n).toFixed(2)}%` }
function formatDecimalNumber(value: any, digits = 4) { const n = Number(value); return isNaN(n) ? '-' : n.toFixed(digits).replace(/\.?0+$/, '') }
function formatPercentNumber(value: any) { const n = Number(value); return isNaN(n) ? '-' : `${(n <= 1 ? n * 100 : n).toFixed(2)}%` }

onMounted(async () => {
  await loadDetail(); await loadParties();
  if (route.query.tab === 'result' || taskDetail.value?.status === 'success') await loadResult()
})
</script>

<style scoped>
/* 页面骨架与标题规范 */
.task-detail-page { min-height: 100vh; background: #f0f2f5; }
.page-header { height: 72px; background: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; }
.title-area h1 { margin: 0; font-size: 20px; color: #1f2937; font-weight: 600; }
.title-area p { margin: 4px 0 0; color: #6b7280; font-size: 13px; }
.page-content { padding: 24px; }
.section-title { margin: 20px 0 16px 0; font-size: 16px; color: #374151; font-weight: 600; border-left: 4px solid #409eff; padding-left: 10px; }
.section-card { margin-top: 16px; border-radius: 8px; border: none; }
.dispatch-entry { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 8px 4px; }
.dispatch-title { font-size: 15px; font-weight: 700; color: #1f2937; margin-bottom: 6px; }
.dispatch-desc { font-size: 13px; color: #64748b; line-height: 1.7; }
.result-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; color: #1f2d3d; display: flex; align-items: center; gap: 6px; }

/* 极客美学组件：Hash 标签 */
.hash-wrapper {
  display: inline-flex; align-items: center; gap: 6px; background: #f3f4f6;
  padding: 4px 10px; border-radius: 6px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s;
}
.hash-wrapper:hover { background: #e5e7eb; border-color: #d1d5db; }
.hash-wrapper.w-full { display: flex; width: 100%; justify-content: flex-start; }
.hash-icon { color: #409eff; font-size: 14px; }
.hash-text { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; color: #374151; }
.mono-text { font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; }
.text-green { color: #10b981; } .text-blue { color: #3b82f6; } .text-danger { color: #ef4444; }

/* 极客美学组件：终端框 (Terminal Box) */
.fl-terminal-box { width: 100%; border-radius: 8px; background: #1e1e1e; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); margin-top: 16px; }
.terminal-header { background: #2d2d2d; padding: 8px 12px; display: flex; align-items: center; border-bottom: 1px solid #404040; position: relative; }
.mac-dots { display: flex; gap: 6px; margin-right: 12px; }
.mac-dots .dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.red { background: #ff5f56; } .dot.yellow { background: #ffbd2e; } .dot.green { background: #27c93f; }
.terminal-title { color: #a0a0a0; font-family: 'Consolas', monospace; font-size: 12px; }
.terminal-header .copy-btn { position: absolute; right: 12px; color: #569cd6; font-size: 12px; font-family: Consolas; }
.terminal-body { padding: 16px; color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; max-height: 400px; overflow-y: auto; }
.terminal-body pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; }

/* 模块面板精调 */
.fl-section-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 16px; }
.fl-info-panel { padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #ffffff; }
.fl-info-panel.dark-panel { background: #1f2937; border-color: #374151; color: #e5e7eb; }
.fl-info-title { font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.fl-info-panel:not(.dark-panel) .fl-info-title { color: #1f2d3d; }
.fl-info-text { line-height: 1.6; font-size: 13px; color: inherit; opacity: 0.85; }

/* 指标卡片 (Metrics Grid) */
.config-metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 16px; }
.config-metric-card { padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; display: flex; justify-content: space-between; align-items: center;}
.config-metric-label { font-size: 13px; color: #6b7280; }
.config-metric-value { font-size: 15px; font-weight: 700; color: #1f2937; font-family: Consolas; }

.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.metric-card { padding: 16px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); transition: transform 0.2s; }
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.metric-label { font-size: 13px; color: #6b7280; margin-bottom: 8px; }
.metric-value { font-size: 24px; font-weight: 700; font-family: Consolas; }

/* 审计面板 */
.audit-panel { border: 1px solid #10b981; border-radius: 8px; padding: 16px; background: #ecfdf5; margin-bottom: 24px; }
.audit-title { font-weight: 700; color: #047857; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }

/* 实用工具类 */
.mt-2 { margin-top: 8px; } .mt-4 { margin-top: 16px; }
.text-sm { font-size: 14px; } .text-xs { font-size: 12px; } .text-gray { color: #9ca3af; }
.mono-input :deep(.el-input__inner) { font-family: 'Consolas', 'Monaco', monospace; }
</style>