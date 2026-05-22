<template>
  <div class="t2-result-page">
    <header class="page-header">
      <div class="title-area">
        <h1>跨区县传染病时空预测与共同暴露分析结果</h1>
        <p>T2 时空轨迹预测任务结果展示</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Back" @click="goDetail">返回详情</el-button>
        <el-button :icon="Refresh" @click="refreshAll">刷新结果</el-button>
        <el-button
          v-if="taskResult && !hasSuccessfulChainAnchor"
          type="warning"
          :icon="Link"
          :loading="anchoring"
          @click="handleAnchorTaskResult"
        >
          结果上链存证
        </el-button>
      </div>
    </header>

    <main class="page-content">
      <!-- 任务结果概览 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="result-header">
            <span class="card-title"><el-icon><DataLine /></el-icon> 任务结果概览</span>
            <el-tag :type="taskDetail?.status === 'success' ? 'success' : 'danger'" effect="dark">
              {{ taskDetail?.status === 'success' ? '执行成功' : '执行失败' }}
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称" :span="2">{{ taskDetail?.task_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="疾病">流感 J10.1</el-descriptions-item>
          <el-descriptions-item label="分析周期">{{ analysisPeriod }}</el-descriptions-item>
          <el-descriptions-item label="结果生成时间">{{ executionInfo?.generated_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结果哈希">
            <div class="hash-wrapper" @click="copyText(taskResult?.result_hash)">
              <el-icon class="hash-icon"><DocumentCopy /></el-icon>
              <span class="hash-text">{{ taskResult?.result_hash || '-' }}</span>
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 核心指标卡片 -->
      <el-card class="section-card" shadow="never" v-if="summary">
        <template #header>
          <span class="card-title"><el-icon><TrendCharts /></el-icon> 核心指标</span>
        </template>
        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-label">参与机构</div>
            <div class="metric-value text-blue">{{ summary.participant_count || 0 }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">参与区县</div>
            <div class="metric-value text-blue">{{ summary.district_count || 0 }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">总病例数</div>
            <div class="metric-value text-blue">{{ summary.total_case_count || 0 }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">阳性数</div>
            <div class="metric-value text-danger">{{ summary.total_positive_count || 0 }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">总体阳性率</div>
            <div class="metric-value">{{ formatRate(summary.overall_positive_rate) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">高风险网格</div>
            <div class="metric-value text-warning">{{ summary.high_risk_grid_count || 0 }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">共同暴露网格</div>
            <div class="metric-value text-warning">{{ summary.common_exposure_grid_count || 0 }}</div>
          </div>
        </div>
      </el-card>

      <!-- 区县风险统计 -->
      <el-card class="section-card" shadow="never" v-if="districtStatistics && districtStatistics.length > 0">
        <template #header>
          <span class="card-title"><el-icon><Location /></el-icon> 区县风险统计</span>
        </template>
        <el-table :data="districtStatistics" border stripe style="width: 100%">
          <el-table-column prop="district_name" label="区县" width="120" />
          <el-table-column prop="case_count" label="病例数" width="100" align="right" />
          <el-table-column prop="positive_count" label="阳性数" width="100" align="right" />
          <el-table-column label="阳性率" width="120" align="right">
            <template #default="{ row }">{{ formatRate(row.positive_rate) }}</template>
          </el-table-column>
          <el-table-column prop="recent_case_count" label="近期病例数" width="120" align="right" />
          <el-table-column label="风险等级" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getRiskLevelType(row.risk_level)" effect="dark">
                {{ getRiskLevelText(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 每日趋势与未来预测 -->
      <el-card class="section-card" shadow="never" v-if="dailyTrend || prediction">
        <template #header>
          <span class="card-title"><el-icon><TrendCharts /></el-icon> 每日趋势与未来预测</span>
        </template>
        
        <div v-if="prediction" class="prediction-section">
          <h4 class="sub-title">未来 7 日预测</h4>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="预测窗口">{{ prediction.prediction_window_days || 7 }} 日</el-descriptions-item>
            <el-descriptions-item label="趋势系数">{{ prediction.trend_factor?.toFixed(4) || '-' }}</el-descriptions-item>
            <el-descriptions-item label="趋势判断">
              <el-tag :type="prediction.trend_level === 'rising' ? 'danger' : 'success'">
                {{ prediction.trend_level === 'rising' ? '上升趋势' : '下降趋势' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="预测病例数">{{ prediction.predicted_total_case_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="预测说明" :span="2">{{ prediction.message || '-' }}</el-descriptions-item>
          </el-descriptions>

          <el-table
            v-if="prediction.district_predictions && prediction.district_predictions.length > 0"
            :data="prediction.district_predictions"
            border
            stripe
            style="width: 100%; margin-top: 16px;"
          >
            <el-table-column prop="district_name" label="区县" width="150" />
            <el-table-column prop="predicted_case_count" label="预测病例数" width="120" align="right" />
            <el-table-column label="风险等级" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="getRiskLevelType(row.risk_level)" effect="plain">
                  {{ getRiskLevelText(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="dailyTrend && dailyTrend.length > 0" class="daily-trend-section">
          <h4 class="sub-title">每日病例趋势</h4>
          <el-table :data="dailyTrend" border stripe style="width: 100%" max-height="400">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="case_count" label="病例数" width="100" align="right" />
            <el-table-column prop="positive_count" label="阳性数" width="100" align="right" />
            <el-table-column label="阳性率" width="120" align="right">
              <template #default="{ row }">{{ formatRate(row.positive_rate) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 高风险空间网格排行 -->
      <el-card class="section-card" shadow="never" v-if="highRiskGrids && highRiskGrids.length > 0">
        <template #header>
          <span class="card-title"><el-icon><Warning /></el-icon> 高风险空间网格排行</span>
        </template>
        <el-table :data="highRiskGrids" border stripe style="width: 100%">
          <el-table-column type="index" label="排名" width="70" align="center" />
          <el-table-column prop="grid_name" label="网格名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="district_name" label="所属区县" width="120" />
          <el-table-column prop="place_type" label="场所类型" width="140" />
          <el-table-column prop="case_count_7d" label="近7日病例数" width="120" align="right" />
          <el-table-column prop="positive_count_7d" label="近7日阳性数" width="120" align="right" />
          <el-table-column label="阳性率" width="100" align="right">
            <template #default="{ row }">{{ formatRate(row.positive_rate_7d) }}</template>
          </el-table-column>
          <el-table-column prop="fever_clinic_visits_7d" label="发热门诊量" width="120" align="right" />
          <el-table-column prop="risk_score" label="风险分数" width="100" align="right">
            <template #default="{ row }">{{ row.risk_score?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="风险等级" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getRiskLevelType(row.risk_level)" effect="dark">
                {{ getRiskLevelText(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 共同暴露区域分析 -->
      <el-card class="section-card" shadow="never" v-if="commonExposureAnalysis && commonExposureAnalysis.length > 0">
        <template #header>
          <span class="card-title"><el-icon><Connection /></el-icon> 共同暴露区域分析</span>
        </template>
        <el-table :data="commonExposureAnalysis" border stripe style="width: 100%">
          <el-table-column prop="grid_name" label="网格名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="district_name" label="所属区县" width="120" />
          <el-table-column prop="place_type" label="场所类型" width="140" />
          <el-table-column prop="exposed_case_count" label="暴露病例数" width="120" align="right" />
          <el-table-column prop="positive_count" label="阳性数" width="100" align="right" />
          <el-table-column label="阳性率" width="100" align="right">
            <template #default="{ row }">{{ formatRate(row.positive_rate) }}</template>
          </el-table-column>
          <el-table-column label="涉及区县" min-width="180">
            <template #default="{ row }">
              <template v-if="row.involved_districts && row.involved_districts.length > 1">
                <el-tag type="danger" effect="dark" style="margin-right: 4px;">跨区县共同暴露</el-tag>
              </template>
              <span>{{ row.involved_districts?.join('、') || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="涉及机构" min-width="180">
            <template #default="{ row }">{{ row.involved_agencies?.join('、') || '-' }}</template>
          </el-table-column>
          <el-table-column prop="risk_reason" label="风险原因" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-card>

      <!-- 参与机构与数据集 -->
      <el-card class="section-card" shadow="never" v-if="participants && participants.length > 0">
        <template #header>
          <span class="card-title"><el-icon><User /></el-icon> 参与机构与数据集</span>
        </template>
        <el-table :data="participants" border stripe style="width: 100%">
          <el-table-column prop="agency_name" label="机构名称" width="180" />
          <el-table-column prop="district_name" label="区县" width="120" />
          <el-table-column prop="node_name" label="节点名称" width="180" />
          <el-table-column prop="dataset_name" label="数据集名称" min-width="200" show-overflow-tooltip />
          <el-table-column label="参与角色" width="180">
            <template #default="{ row }">
              <template v-if="row.roles && row.roles.length > 0">
                <el-tag v-for="role in row.roles" :key="role" :type="role === 'data_provider' ? 'success' : 'info'" effect="plain" style="margin-right: 4px;">
                  {{ getRoleText(role) }}
                </el-tag>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="case_count" label="病例数" width="100" align="right" />
          <el-table-column prop="positive_count" label="阳性数" width="100" align="right" />
        </el-table>
      </el-card>

      <!-- 可信存证区域 -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <div class="result-header">
            <span class="card-title"><el-icon><Link /></el-icon> 可信存证</span>
            <el-tag :type="hasSuccessfulChainAnchor ? 'success' : 'info'">
              {{ hasSuccessfulChainAnchor ? '已完成存证' : '待存证' }}
            </el-tag>
          </div>
        </template>

        <template v-if="chainAnchorResult?.chain_record">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="链类型">{{ chainAnchorResult.chain_record.chain_type || 'FISCO BCOS' }}</el-descriptions-item>
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
            <el-descriptions-item label="存证时间">{{ chainAnchorResult.chain_record.chain_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="内容哈希">
              <div class="hash-wrapper w-full" @click="copyText(chainAnchorResult.chain_record.content_hash)">
                <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                <span class="hash-text">{{ chainAnchorResult.chain_record.content_hash || '-' }}</span>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </template>
        <el-empty v-else description="任务结果尚未上链，可点击右上角按钮进行区块链存证" />
      </el-card>

      <!-- 底层回执 JSON -->
      <el-card class="section-card" shadow="never">
        <template #header>
          <span class="card-title"><el-icon><DocumentCopy /></el-icon> 底层回执 JSON</span>
        </template>
        <div class="fl-terminal-box">
          <div class="terminal-header">
            <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
            <span class="terminal-title">task_result.json</span>
            <el-button link class="copy-btn" @click="copyText(formatJson(resultJson))">Copy</el-button>
          </div>
          <div class="terminal-body">
            <pre>{{ formatJson(resultJson) }}</pre>
          </div>
        </div>
      </el-card>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Back,
  Refresh,
  Link,
  DataLine,
  DocumentCopy,
  Connection,
  TrendCharts,
  Location,
  Warning,
  User,
} from '@element-plus/icons-vue'

import { anchorTaskResult, getTaskDetail, getTaskResult } from '@/api/task'
import { getChainRecordList } from '@/api/chainRecord'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const loading = ref(false)
const anchoring = ref(false)
const taskDetail = ref<any>(null)
const taskResult = ref<any>(null)
const chainAnchorResult = ref<any>(null)

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

const resultJson = computed(() => {
  if (!taskResult.value?.result_json) return {}
  const json = taskResult.value.result_json
  if (typeof json === 'string') {
    try {
      return JSON.parse(json)
    } catch {
      return {}
    }
  }
  return json
})

const summary = computed(() => resultJson.value.summary || null)
const districtStatistics = computed(() => resultJson.value.district_statistics || [])
const dailyTrend = computed(() => resultJson.value.daily_trend || [])
const prediction = computed(() => resultJson.value.prediction || null)
const highRiskGrids = computed(() => resultJson.value.high_risk_grids || [])
const commonExposureAnalysis = computed(() => resultJson.value.common_exposure_analysis || [])
const participants = computed(() => resultJson.value.participants || [])
const auxiliaryDatasets = computed(() => resultJson.value.auxiliary_datasets || null)
const executionInfo = computed(() => resultJson.value.execution_info || null)

const analysisPeriod = computed(() => {
  const params = resultJson.value.params || {}
  const start = params.analysis_start_date || taskDetail.value?.stat_start_time?.substring(0, 10) || '2026-04-01'
  const end = params.analysis_end_date || taskDetail.value?.stat_end_time?.substring(0, 10) || '2026-04-30'
  return `${start} 至 ${end}`
})

const hasSuccessfulChainAnchor = computed(() => {
  return chainAnchorResult.value?.chain_record?.tx_hash
})

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

async function loadResult() {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
    await loadChainRecordForCurrentResult()
  } catch (error) {
    taskResult.value = null
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
  await loadResult()
}

function goDetail() {
  router.push(`/tasks/${taskId}`)
}

async function copyText(text: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

function formatRate(value: any) {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

function formatJson(obj: any) {
  return JSON.stringify(obj, null, 2)
}

function getRiskLevelType(level: string) {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success',
  }
  return map[level] || 'info'
}

function getRiskLevelText(level: string) {
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  }
  return map[level] || level
}

function getRoleText(role: string) {
  const map: Record<string, string> = {
    data_provider: '数据提供方',
    result_receiver: '结果接收方',
    compute_provider: '计算参与方',
    coordinator: '协调方',
  }
  return map[role] || role
}

async function handleAnchorTaskResult() {
  if (!taskResult.value) {
    ElMessage.warning('暂无任务结果')
    return
  }

  anchoring.value = true
  try {
    await anchorTaskResult(taskId)
    ElMessage.success('任务结果已成功上链存证')
    await loadChainRecordForCurrentResult()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || '上链存证失败'
    ElMessage.error(detail)
  } finally {
    anchoring.value = false
  }
}

onMounted(async () => {
  await refreshAll()
})
</script>

<style scoped>
.t2-result-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-area h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a1a;
}

.title-area p {
  color: #666;
  margin: 0;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.section-card {
  margin-bottom: 20px;
  background: #fff;
}

.card-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 8px;
}

.metric-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: all 0.3s;
}

.metric-card:hover {
  background: #eef1f6;
  transform: translateY(-2px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.metric-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.text-blue {
  color: #409eff;
}

.text-danger {
  color: #f56c6c;
}

.text-warning {
  color: #e6a23c;
}

.text-success {
  color: #67c23a;
}

.text-purple {
  color: #9b59b6;
}

.hash-wrapper {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.3s;
  max-width: 100%;
}

.hash-wrapper:hover {
  background: #f5f7fa;
}

.hash-wrapper.w-full {
  width: 100%;
}

.hash-icon {
  margin-right: 6px;
  color: #409eff;
  flex-shrink: 0;
}

.hash-text {
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #303133;
}

.prediction-section {
  margin-bottom: 24px;
}

.daily-trend-section {
  margin-top: 24px;
}

.fl-terminal-box {
  background: #1e1e1e;
  border-radius: 6px;
  overflow: hidden;
  font-family: 'Courier New', Courier, monospace;
}

.terminal-header {
  background: #2d2d2d;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.red {
  background: #ff5f56;
}

.dot.yellow {
  background: #ffbd2e;
}

.dot.green {
  background: #27c93a;
}

.terminal-title {
  flex: 1;
  color: #999;
  font-size: 13px;
  margin-left: 8px;
}

.copy-btn {
  color: #409eff;
}

.terminal-body {
  padding: 16px;
  color: #d4d4d4;
  font-size: 13px;
  max-height: 600px;
  overflow-y: auto;
}

.terminal-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.mt-4 {
  margin-top: 16px;
}
</style>
