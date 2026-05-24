<template>
  <div class="task-result-page">
    <!-- T2 任务使用专用结果页面 -->
    <T2TaskResultView v-if="isT2Task" />

    <!-- T3 任务使用疫苗效果评估专用结果页面 -->
    <T3TaskResultView v-else-if="isT3Task" />

    <!-- T4 任务使用高血压危险因素交互分析专用结果页面 -->
    <T4TaskResultView v-else-if="isT4Task" />

    <!-- 其他任务使用原有结果页面 -->
    <template v-else>
      <header class="page-header">
      <div class="title-area">
        <h1>联邦计算结果</h1>
        <p>先展示训练过程动画，训练结束后展示指标、结果哈希与链上存证信息</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Back" @click="goDetail">返回详情</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新结果</el-button>
        <el-button
          v-if="taskResult"
          type="warning"
          :icon="Link"
          :loading="anchoring"
          :disabled="taskDetail?.status !== 'success' || hasSuccessfulChainAnchor"
          @click="handleAnchorTaskResult"
        >
          {{ anchorButtonText }}
        </el-button>
      </div>
    </header>

    <main class="page-content">
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="result-header">
            <span class="card-title"><el-icon><VideoPlay /></el-icon> 训练过程</span>
            <el-tag :type="runStageTagType" effect="dark">{{ runStageText }}</el-tag>
          </div>
        </template>

        <FederatedAnimation
          v-if="showAnimation"
          :parties="animationParties"
          :total-rounds="totalRounds"
        />

        <div v-if="running" class="running-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          SecretFlow 联邦训练正在执行，请保持当前页面打开。训练完成后将自动展示结果。
        </div>
      </el-card>

      <template v-if="taskResult">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="result-header">
              <span class="card-title"><el-icon><DataLine /></el-icon> 训练结果</span>
              <el-tag type="success" effect="plain">{{ resultFramework }}</el-tag>
            </div>
          </template>

          <div class="metric-grid" v-if="isFederatedLearningTask(taskDetail)">
            <div class="metric-card"><div class="metric-label">Accuracy</div><div class="metric-value text-blue">{{ formatPercentNumber(federatedSummary.final_accuracy) }}</div></div>
            <div class="metric-card"><div class="metric-label">AUC</div><div class="metric-value text-green">{{ formatDecimalNumber(federatedSummary.final_auc) }}</div></div>
            <div class="metric-card"><div class="metric-label">Precision</div><div class="metric-value">{{ formatPercentNumber(federatedSummary.final_precision) }}</div></div>
            <div class="metric-card"><div class="metric-label">Recall</div><div class="metric-value">{{ formatPercentNumber(federatedSummary.final_recall) }}</div></div>
            <div class="metric-card"><div class="metric-label">F1</div><div class="metric-value text-purple">{{ formatDecimalNumber(federatedSummary.final_f1) }}</div></div>
            <div class="metric-card"><div class="metric-label">样本总数</div><div class="metric-value">{{ formatMetricNumber(federatedSummary.sample_count) }}</div></div>
            <div class="metric-card"><div class="metric-label">训练轮次</div><div class="metric-value">{{ federatedSummary.round_count ?? '-' }}</div></div>
            <div class="metric-card"><div class="metric-label">参与方数量</div><div class="metric-value">{{ federatedSummary.participant_count ?? '-' }}</div></div>
          </div>

          <div class="metric-grid" v-else>
            <div class="metric-card"><div class="metric-label">病例数</div><div class="metric-value text-blue">{{ formatMetricNumber(resultMetrics.case_count) }}</div></div>
            <div class="metric-card"><div class="metric-label">去重人数</div><div class="metric-value text-green">{{ formatMetricNumber(resultMetrics.unique_patient_count) }}</div></div>
            <div class="metric-card"><div class="metric-label">阳性数</div><div class="metric-value text-danger">{{ formatMetricNumber(resultMetrics.positive_count) }}</div></div>
            <div class="metric-card"><div class="metric-label">阳性率</div><div class="metric-value">{{ formatRate(resultMetrics.positive_rate) }}</div></div>
          </div>

          <el-descriptions :column="2" border class="mt-4">
            <el-descriptions-item label="任务编号">{{ taskDetail?.task_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="任务状态">
              <el-tag :type="getStatusType(taskDetail?.status)">{{ getStatusText(taskDetail?.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="模型类型" v-if="isFederatedLearningTask(taskDetail)">{{ modelTypeText }}</el-descriptions-item>
            <el-descriptions-item label="聚合方式" v-if="isFederatedLearningTask(taskDetail)">{{ federatedSummary.privacy_mode || resultJson.aggregator || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结果哈希" :span="2">
              <div class="hash-wrapper w-full" @click="copyText(taskResult.result_hash)">
                <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                <span class="hash-text">{{ taskResult.result_hash || '-' }}</span>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card v-if="partyMetricRows.length" class="section-card" shadow="never">
          <template #header>
            <span class="card-title"><el-icon><Connection /></el-icon> 分方训练指标</span>
          </template>
          <el-table :data="partyMetricRows" border stripe style="width: 100%">
            <el-table-column prop="party" label="参与方" width="120" />
            <el-table-column prop="sample_count" label="样本数" width="120" align="right" />
            <el-table-column label="Accuracy" align="right"><template #default="{ row }">{{ formatPercentNumber(row.accuracy) }}</template></el-table-column>
            <el-table-column label="AUC" align="right"><template #default="{ row }">{{ formatDecimalNumber(row.auc) }}</template></el-table-column>
            <el-table-column label="Precision" align="right"><template #default="{ row }">{{ formatPercentNumber(row.precision) }}</template></el-table-column>
            <el-table-column label="Recall" align="right"><template #default="{ row }">{{ formatPercentNumber(row.recall) }}</template></el-table-column>
            <el-table-column label="F1" align="right"><template #default="{ row }">{{ formatDecimalNumber(row.f1) }}</template></el-table-column>
          </el-table>
        </el-card>

        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="result-header">
              <span class="card-title"><el-icon><Monitor /></el-icon> 链上存证</span>
              <el-tag :type="hasSuccessfulChainAnchor ? 'success' : 'info'">
                {{ hasSuccessfulChainAnchor ? '已完成存证' : '待存证' }}
              </el-tag>
            </div>
          </template>

          <template v-if="chainAnchorResult?.chain_record">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="链类型">{{ formatChainType(chainAnchorResult.chain_record.chain_type) }}</el-descriptions-item>
              <el-descriptions-item label="区块高度"># {{ chainAnchorResult.chain_record.block_number || '-' }}</el-descriptions-item>
              <el-descriptions-item label="交易哈希" :span="2">
                <div class="hash-wrapper w-full" @click="copyText(chainAnchorResult.chain_record.tx_hash)">
                  <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                  <span class="hash-text">{{ chainAnchorResult.chain_record.tx_hash || '-' }}</span>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="合约地址" :span="2">
                <div class="hash-wrapper w-full" @click="copyText(chainAnchorResult.chain_record.contract_address)">
                  <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                  <span class="hash-text">{{ chainAnchorResult.chain_record.contract_address || '-' }}</span>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="内容哈希" :span="2">
                <div class="hash-wrapper w-full" @click="copyText(chainAnchorResult.chain_record.content_hash)">
                  <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                  <span class="hash-text">{{ chainAnchorResult.chain_record.content_hash || '-' }}</span>
                </div>
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="训练结果尚未上链，可点击右上角签发至区块链" />
        </el-card>

        <el-card class="section-card" shadow="never">
          <template #header>
            <span class="card-title"><el-icon><DocumentCopy /></el-icon> 底层回执 JSON</span>
          </template>
          <div class="fl-terminal-box">
            <div class="terminal-header">
              <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
              <span class="terminal-title">core_engine_output.json</span>
              <el-button link class="copy-btn" @click="copyText(formatJson(taskResult.result_json || taskResult.metrics_json || taskResult))">Copy</el-button>
            </div>
            <div class="terminal-body">
              <pre>{{ formatJson(taskResult.result_json || taskResult.metrics_json || taskResult) }}</pre>
            </div>
          </div>
        </el-card>
      </template>

      <el-card v-else-if="!running" class="section-card" shadow="never">
        <el-empty description="暂无结果。请在任务详情页点击执行任务按钮。" />
      </el-card>
    </main>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Back,
  Refresh,
  Link,
  VideoPlay,
  Loading,
  DataLine,
  DocumentCopy,
  Connection,
  Monitor,
} from '@element-plus/icons-vue'

import { anchorTaskResult, getTaskDetail, getTaskParties, getTaskResult, runTask } from '@/api/task'
import { getChainRecordList } from '@/api/chainRecord'
import { isFederatedLearningTask, parseJsonValue } from '@/constants/taskScenario'
import FederatedAnimation from '@/components/FederatedAnimation.vue'
import T2TaskResultView from './T2TaskResultView.vue'
import T3TaskResultView from './T3TaskResultView.vue'
import T4TaskResultView from './T4TaskResultView.vue'

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
const runStage = ref<'idle' | 'running' | 'success' | 'failed'>('idle')

const isT2Task = computed(() => {
  if (!taskDetail.value) return false
  const paramsJson = taskDetail.value.params_json || {}
  const templateCode = paramsJson.template_code || taskDetail.value.template_code || ''
  return templateCode.startsWith('T2')
})

const isT3Task = computed(() => {
  if (!taskDetail.value) return false

  const paramsJson = taskDetail.value.params_json || {}
  const templateCode = String(paramsJson.template_code || taskDetail.value.template_code || '')
  const taskCode = String(taskDetail.value.task_code || '')
  const taskName = String(taskDetail.value.task_name || '')

  return (
    templateCode === 'T3_VACCINE_EFFECT_EVALUATION_TEMPLATE' ||
    templateCode.startsWith('T3') ||
    taskCode.includes('T3_VACCINE_EFFECT') ||
    taskName.includes('疫苗') ||
    taskName.includes('接种') ||
    taskName.includes('保护效果')
  )
})

const isT4Task = computed(() => {
  if (!taskDetail.value) return false

  const paramsJson = taskDetail.value.params_json || {}
  const templateCode = String(paramsJson.template_code || taskDetail.value.template_code || '').toUpperCase()
  const taskCode = String(taskDetail.value.task_code || '').toUpperCase()
  const taskName = String(taskDetail.value.task_name || '')
  const description = String(taskDetail.value.description || '')
  const templateId = Number(taskDetail.value.template_id || 0)

  return (
    templateCode === 'T4_HYPERTENSION_FACTOR_INTERACTION_TEMPLATE' ||
    templateCode.startsWith('T4_HYPERTENSION') ||
    taskCode.includes('T4_HYPERTENSION') ||
    taskName.includes('高血压') ||
    description.includes('高血压') ||
    templateId === 7
  )
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
    taskDetail.value = unwrapResponse(await getTaskDetail(taskId))
  } catch (error) {
    ElMessage.error('任务详情加载失败')
  } finally {
    loading.value = false
  }
}

async function loadParties() {
  try {
    partyList.value = normalizeList(unwrapResponse(await getTaskParties(taskId)))
  } catch (error) {
    partyList.value = []
  }
}

async function loadResult(silent = false) {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
    await loadChainRecordForCurrentResult()
  } catch (error) {
    if (!silent) taskResult.value = null
  }
}

async function loadChainRecordForCurrentResult() {
  if (!taskResult.value?.id) {
    chainAnchorResult.value = null
    return
  }

  try {
    const data = unwrapResponse(await getChainRecordList({
      page: 1,
      page_size: 1,
      biz_type: 'task_result',
      biz_id: String(taskResult.value.id),
      status: 'success',
    })) || {}

    const record = Array.isArray(data.items) ? data.items[0] : null
    chainAnchorResult.value = record
      ? { anchored: true, duplicated: true, message: '当前任务结果已完成 FISCO BCOS 链上存证', chain_record: record }
      : null
  } catch (error) {
    console.warn('存证记录加载失败', error)
  }
}

async function refreshAll() {
  await loadDetail()
  await loadParties()
  await loadResult(true)
  if (taskResult.value) runStage.value = 'success'
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function isRequestTimeoutOrNetworkError(error: any) {
  const code = String(error?.code || '')
  const message = String(error?.message || '')
  const status = error?.response?.status
  return code === 'ECONNABORTED' || code === 'ERR_NETWORK' || status === 504 || message.includes('timeout') || message.includes('Network') || message.includes('网络')
}

async function recoverRunSuccessAfterRequestError() {
  for (let i = 0; i < 15; i += 1) {
    await sleep(i === 0 ? 1000 : 5000)
    await refreshAll()
    if (taskDetail.value?.status === 'success' || taskResult.value?.status === 'success' || taskResult.value?.result_hash) {
      runStage.value = 'success'
      ElMessage.success('计算任务已在后台完成，结果已刷新')
      return true
    }
  }
  return false
}

async function handleRun() {
  if (!taskDetail.value) return
  if (!partyList.value.length) {
    ElMessage.warning('请先配置计算拓扑节点')
    return
  }

  // 清空旧结果，避免误导
  taskResult.value = null
  chainAnchorResult.value = null
  running.value = true
  runStage.value = 'running'

  // 确保动画至少显示 5 秒
  const minAnimationTime = 5000
  const startTime = Date.now()

  try {
    const data = unwrapResponse(await runTask(taskId))
    if (data?.result) taskResult.value = data.result
    await refreshAll()
    runStage.value = 'success'
    ElMessage.success('计算完成，结果已生成')
  } catch (error: any) {
    if (isRequestTimeoutOrNetworkError(error)) {
      ElMessage.warning('训练请求仍在后台执行，正在自动监听结果...')
      if (await recoverRunSuccessAfterRequestError()) return
    }

    runStage.value = 'failed'
    ElMessage.error('计算执行失败，请检查底层服务日志')
    await loadDetail()
  } finally {
    // 计算还需要等待多久，确保动画至少显示 5 秒
    const elapsed = Date.now() - startTime
    const remainingTime = Math.max(0, minAnimationTime - elapsed)
    
    if (remainingTime > 0) {
      await new Promise(resolve => setTimeout(resolve, remainingTime))
    }
    
    running.value = false
  }
}

async function handleAnchorTaskResult() {
  if (!taskDetail.value || taskDetail.value.status !== 'success') {
    ElMessage.warning('任务尚未成功完成，不能存证')
    return
  }
  if (!taskResult.value) {
    ElMessage.warning('暂无可存证结果')
    return
  }

  try {
    await ElMessageBox.confirm('确认将当前结果摘要写入 FISCO BCOS 联盟链？', '上链确认', {
      type: 'warning',
      confirmButtonText: '确认上链',
      cancelButtonText: '取消',
    })

    anchoring.value = true
    const data = unwrapResponse(await anchorTaskResult(taskId))
    chainAnchorResult.value = data
    if (data?.duplicated) ElMessage.info(data.message || '当前结果已完成存证')
    else ElMessage.success(data?.message || '任务结果真实上链存证成功')
    await loadChainRecordForCurrentResult()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('上链存证失败')
  } finally {
    anchoring.value = false
  }
}

function goDetail() {
  router.push(`/tasks/${taskId}`)
}

async function copyText(text: string) {
  if (!text || text === '-') return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

function formatJson(value: any) {
  if (!value) return '-'
  try {
    return typeof value === 'string' ? JSON.stringify(JSON.parse(value), null, 2) : JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const resultJson = computed(() => parseJsonValue(taskResult.value?.result_json))
const metricsJson = computed(() => parseJsonValue(taskResult.value?.metrics_json))

const federatedSummary = computed(() => {
  const r = resultJson.value || {}
  const m = metricsJson.value || {}
  const s = r.summary || {}
  return {
    final_accuracy: s.final_accuracy ?? m.final_accuracy ?? r.metrics?.accuracy,
    final_auc: s.final_auc ?? m.final_auc ?? r.metrics?.auc,
    final_precision: s.final_precision ?? m.final_precision ?? r.metrics?.precision,
    final_recall: s.final_recall ?? m.final_recall ?? r.metrics?.recall,
    final_f1: s.final_f1 ?? m.final_f1 ?? r.metrics?.f1,
    round_count: s.round_count ?? m.round_count ?? r.training_params?.epochs,
    participant_count: s.participant_count ?? m.participant_count ?? r.participants?.length,
    sample_count: s.sample_count ?? m.sample_count ?? r.metrics?.sample_count,
    privacy_mode: s.privacy_mode ?? m.privacy_mode ?? r.aggregator,
  }
})

const resultMetrics = computed(() => {
  const r = resultJson.value || {}
  const m = metricsJson.value || {}
  const s = { ...m, ...r }
  return {
    case_count: s.case_count ?? s.metrics?.case_count ?? null,
    unique_patient_count: s.unique_patient_count ?? s.metrics?.unique_patient_count ?? null,
    positive_count: s.positive_count ?? s.metrics?.positive_count ?? null,
    positive_rate: s.positive_rate ?? s.metrics?.positive_rate ?? null,
  }
})

const partyMetricRows = computed(() => {
  const metricsByParty = resultJson.value?.metrics_by_party || {}
  return Object.entries(metricsByParty).map(([party, value]: [string, any]) => ({
    party,
    ...value,
  }))
})

const totalRounds = computed(() => Number(federatedSummary.value.round_count || resultJson.value?.training_params?.epochs || 5))

const animationParties = computed(() => {
  if (partyList.value.length) return partyList.value
  return [
    { node_id: 'alice', node_name: 'Alice 本地训练节点', power: 8, status: 'idle' },
    { node_id: 'bob', node_name: 'Bob 本地训练节点', power: 8, status: 'idle' },
  ]
})

const showAnimation = computed(() => running.value || !taskResult.value)
const hasSuccessfulChainAnchor = computed(() => chainAnchorResult.value?.chain_record?.status === 'success')
const anchorButtonText = computed(() => hasSuccessfulChainAnchor.value ? '已完成存证' : '签发至区块链')
const resultFramework = computed(() => resultJson.value?.framework === 'secretflow' ? 'SecretFlow' : resultJson.value?.framework || '-')
const modelTypeText = computed(() => resultJson.value?.model_type === 'FLModel_torch_mlp_binary_classifier' ? 'FLModel + Torch MLP 二分类模型' : resultJson.value?.model_type || '-')
const runStageText = computed(() => ({ idle: '等待下发', running: '训练中', success: '训练完成', failed: '执行异常' }[runStage.value]))
const runStageTagType = computed(() => ({ idle: 'info', running: 'warning', success: 'success', failed: 'danger' }[runStage.value]))

function getStatusText(status: string) {
  const map: Record<string, string> = { created: '已编排', pending: '等待中', running: '计算中', success: '执行成功', failed: '执行失败' }
  return map[status] || status || '-'
}

function getStatusType(status: string) {
  const map: Record<string, string> = { created: 'info', pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function formatMetricNumber(value: any) {
  return value == null || value === '' ? '-' : Number(value).toLocaleString()
}

function formatRate(value: any) {
  const n = Number(value)
  return Number.isNaN(n) ? '-' : `${(n <= 1 ? n * 100 : n).toFixed(2)}%`
}

function formatDecimalNumber(value: any, digits = 4) {
  const n = Number(value)
  return Number.isNaN(n) ? '-' : n.toFixed(digits).replace(/\.?0+$/, '')
}

function formatPercentNumber(value: any) {
  const n = Number(value)
  return Number.isNaN(n) ? '-' : `${(n <= 1 ? n * 100 : n).toFixed(2)}%`
}

function formatChainType(type: string) {
  return type === 'fisco_bcos' ? 'FISCO BCOS' : type || '-'
}

onMounted(async () => {
  await loadDetail()
  await loadParties()

  if (route.query.autoRun === '1') {
    await handleRun()
  } else {
    await loadResult(true)
    if (taskResult.value) runStage.value = 'success'
  }
})
</script>

<style scoped>
.task-result-page { min-height: 100vh; background: #f0f2f5; }
.page-header { height: 72px; background: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; }
.title-area h1 { margin: 0; font-size: 20px; color: #1f2937; font-weight: 600; }
.title-area p { margin: 4px 0 0; color: #6b7280; font-size: 13px; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.page-content { padding: 24px; }
.section-card { margin-bottom: 16px; border-radius: 8px; border: none; }
.result-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; color: #1f2d3d; display: flex; align-items: center; gap: 6px; }
.running-tip { margin-top: 12px; padding: 12px 14px; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 8px; display: flex; align-items: center; gap: 8px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 18px; }
.metric-card { padding: 16px; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; }
.metric-label { font-size: 13px; color: #6b7280; margin-bottom: 8px; }
.metric-value { font-size: 24px; font-weight: 700; font-family: Consolas, Monaco, monospace; color: #1f2937; }
.text-green { color: #10b981; }
.text-blue { color: #3b82f6; }
.text-danger { color: #ef4444; }
.text-purple { color: #7c3aed; }
.mt-4 { margin-top: 16px; }
.hash-wrapper { display: inline-flex; align-items: center; gap: 6px; background: #f3f4f6; padding: 4px 10px; border-radius: 6px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s; }
.hash-wrapper:hover { background: #e5e7eb; }
.hash-wrapper.w-full { display: flex; width: 100%; }
.hash-icon { color: #409eff; font-size: 14px; }
.hash-text { font-family: Consolas, Monaco, monospace; font-size: 13px; color: #374151; word-break: break-all; }
.fl-terminal-box { width: 100%; border-radius: 8px; background: #1e1e1e; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }
.terminal-header { background: #2d2d2d; padding: 8px 12px; display: flex; align-items: center; border-bottom: 1px solid #404040; position: relative; }
.dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }
.terminal-title { color: #a0a0a0; font-family: Consolas, Monaco, monospace; font-size: 12px; margin-left: 6px; }
.copy-btn { position: absolute; right: 12px; color: #569cd6; }
.terminal-body { padding: 16px; color: #d4d4d4; font-family: Consolas, Monaco, monospace; font-size: 13px; line-height: 1.6; max-height: 400px; overflow-y: auto; }
.terminal-body pre { margin: 0; white-space: pre-wrap; word-break: break-word; }
@media (max-width: 1200px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
