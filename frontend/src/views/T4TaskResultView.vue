<template>
  <div class="t4-result-page">
    <header class="page-header">
      <div class="title-area">
        <h1>高血压危险因素交互作用安全分析</h1>
        <p>展示高血压检出率、区县/年龄/性别分层、单因素风险、双因素交互风险与近似回归系数</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Back" @click="goDetail">返回详情</el-button>
        <el-button :icon="Refresh" :loading="refreshing" @click="refreshAll">刷新结果</el-button>
      </div>
    </header>

    <main class="page-content">
      <div v-if="running" class="glass-card running-card">
        <div class="result-header">
          <span class="card-title"><el-icon><VideoPlay /></el-icon> 高血压危险因素交互分析执行中</span>
          <el-tag type="warning" effect="dark">执行中</el-tag>
        </div>

        <FederatedAnimation
          :parties="animationParties"
          :total-rounds="8"
          task-name="高血压危险因素交互作用安全分析任务"
        />

        <div class="running-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在执行三方本地统计、OR 与交互风险计算，请稍候...</span>
        </div>
      </div>

      <el-empty
        v-else-if="!hasResult"
        class="empty-result"
        description="暂无结果数据，请先在任务详情页执行任务"
      />

      <template v-else>
        <section class="overview-section">
          <div class="overview-main glass-card">
            <div class="overview-title">
              <div>
                <h2>三城区高血压风险分析结果</h2>
                <p>{{ taskCodeText }}</p>
              </div>
              <span class="risk-pill">{{ riskLevelText }}</span>
            </div>

            <div class="metric-grid">
              <div class="metric-card blue">
                <span class="metric-label">总调查人数</span>
                <strong>{{ formatInteger(summary.total_count) }}</strong>
              </div>
              <div class="metric-card danger">
                <span class="metric-label">高血压人数</span>
                <strong>{{ formatInteger(summary.hypertension_count) }}</strong>
              </div>
              <div class="metric-card warning">
                <span class="metric-label">高血压检出率</span>
                <strong>{{ formatRate(summary.hypertension_rate) }}</strong>
              </div>
              <div class="metric-card cyan">
                <span class="metric-label">高风险人数</span>
                <strong>{{ formatInteger(summary.high_risk_count) }}</strong>
              </div>
              <div class="metric-card purple">
                <span class="metric-label">最高单因素</span>
                <strong class="text-fit">{{ summary.top_single_factor || '-' }}</strong>
                <small>OR {{ formatNumber(summary.top_single_factor_or) }}</small>
              </div>
              <div class="metric-card sky">
                <span class="metric-label">最高交互项</span>
                <strong class="text-fit">{{ summary.top_interaction_factor || '-' }}</strong>
                <small>OR {{ formatNumber(summary.top_interaction_factor_or) }}</small>
              </div>
            </div>
          </div>

          <div class="interpretation-card glass-card">
            <div class="section-title compact">
              <el-icon><Warning /></el-icon>
              <span>分析结论</span>
            </div>
            <div class="interpretation-list">
              <div class="interpretation-item">
                <el-tag type="danger" effect="light" size="small">最高单因素</el-tag>
                <p>
                  {{ summary.top_single_factor || '-' }}
                  <template v-if="summary.top_single_factor_or">
                    的 OR 值为 {{ formatNumber(summary.top_single_factor_or) }}。
                  </template>
                </p>
              </div>
              <div class="interpretation-item">
                <el-tag type="warning" effect="light" size="small">最高交互项</el-tag>
                <p>
                  {{ summary.top_interaction_factor || '-' }}
                  <template v-if="summary.top_interaction_factor_or">
                    的 OR 值为 {{ formatNumber(summary.top_interaction_factor_or) }}。
                  </template>
                </p>
              </div>
              <div class="interpretation-item">
                <el-tag type="primary" effect="light" size="small">数据口径</el-tag>
                <p>结果仅展示三方聚合统计、OR 值与近似回归系数，不展示个体原始数据。</p>
              </div>
            </div>
          </div>
        </section>

        <section class="chart-grid two-columns">
          <div class="glass-card chart-card" v-if="districtStatistics.length">
            <div class="section-title">
              <el-icon><Histogram /></el-icon>
              <span>区县高血压检出率</span>
            </div>
            <div ref="districtChartRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-card" v-if="ageGroupStatistics.length">
            <div class="section-title">
              <el-icon><TrendCharts /></el-icon>
              <span>年龄段高血压检出率</span>
            </div>
            <div ref="ageChartRef" class="chart-box"></div>
          </div>
        </section>

        <section class="chart-grid two-columns">
          <div class="glass-card chart-card" v-if="genderStatistics.length">
            <div class="section-title">
              <el-icon><DataLine /></el-icon>
              <span>性别分层高血压检出率</span>
            </div>
            <div ref="genderChartRef" class="chart-box"></div>
            <div class="chart-note">该图展示男女各自组内高血压检出率，不是男女构成占比。</div>
          </div>

          <div class="glass-card chart-card" v-if="singleFactorRows.length">
            <div class="section-title">
              <el-icon><DataLine /></el-icon>
              <span>单因素风险排行</span>
            </div>
            <div ref="singleChartRef" class="chart-box"></div>
          </div>
        </section>

        <section class="glass-card chart-card" v-if="interactionRows.length">
          <div class="section-title">
            <el-icon><DataLine /></el-icon>
            <span>双因素交互风险排行</span>
          </div>
          <div ref="interactionChartRef" class="wide-chart-box"></div>
        </section>

        <section class="table-grid two-columns">
          <div class="glass-card table-card" v-if="singleFactorRows.length">
            <div class="section-title table-title">
              <el-icon><DataLine /></el-icon>
              <span>单因素风险明细</span>
            </div>
            <el-table class="pretty-table" :data="singleFactorRows" border stripe height="410">
              <el-table-column prop="rank" label="排名" width="68" align="center" />
              <el-table-column prop="factor_name" label="危险因素" width="130" />
              <el-table-column prop="description" label="判定口径" min-width="210" show-overflow-tooltip />
              <el-table-column label="暴露组检出率" width="126" align="center">
                <template #default="{ row }">
                  <span class="rate-strong">{{ displayPercent(row, 'exposed_hypertension_rate', 'exposed_hypertension_rate_percent') }}</span>
                </template>
              </el-table-column>
              <el-table-column label="非暴露组检出率" width="140" align="center">
                <template #default="{ row }">
                  {{ displayPercent(row, 'non_exposed_hypertension_rate', 'non_exposed_hypertension_rate_percent') }}
                </template>
              </el-table-column>
              <el-table-column label="OR" width="88" align="center">
                <template #default="{ row }">
                  <el-tag :type="getOrTagType(row.or_value)" effect="plain">{{ formatNumber(row.or_value) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="方向" width="104" align="center">
                <template #default="{ row }">
                  <span :class="getDirectionClass(row.risk_direction)">{{ row.risk_direction || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="glass-card table-card" v-if="interactionRows.length">
            <div class="section-title table-title">
              <el-icon><DataLine /></el-icon>
              <span>双因素交互明细</span>
            </div>
            <el-table class="pretty-table" :data="interactionRows" border stripe height="410">
              <el-table-column prop="rank" label="排名" width="68" align="center" />
              <el-table-column prop="interaction_name" label="交互组合" min-width="170" show-overflow-tooltip />
              <el-table-column label="组合暴露人数" width="118" align="right">
                <template #default="{ row }">{{ formatInteger(row.combined_exposed_total) }}</template>
              </el-table-column>
              <el-table-column label="组合检出率" width="118" align="center">
                <template #default="{ row }">
                  <span class="rate-strong">{{ displayPercent(row, 'combined_hypertension_rate', 'combined_hypertension_rate_percent') }}</span>
                </template>
              </el-table-column>
              <el-table-column label="对照检出率" width="118" align="center">
                <template #default="{ row }">
                  {{ displayPercent(row, 'comparison_hypertension_rate', 'comparison_hypertension_rate_percent') }}
                </template>
              </el-table-column>
              <el-table-column label="OR" width="88" align="center">
                <template #default="{ row }">
                  <el-tag :type="getOrTagType(row.or_value)" effect="plain">{{ formatNumber(row.or_value) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="方向" width="104" align="center">
                <template #default="{ row }">
                  <span :class="getDirectionClass(row.risk_direction)">{{ row.risk_direction || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </section>

        <section class="glass-card table-card" v-if="regressionRows.length">
          <div class="section-title table-title">
            <el-icon><DataLine /></el-icon>
            <span>近似回归系数结果</span>
          </div>
          <el-table class="pretty-table" :data="regressionRows" border stripe>
            <el-table-column prop="term_name" label="因素 / 交互项" min-width="220" show-overflow-tooltip />
            <el-table-column label="类型" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.term_type === 'interaction' ? 'warning' : 'primary'" effect="light">
                  {{ row.term_type === 'interaction' ? '交互项' : '单因素' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="系数" width="100" align="right">
              <template #default="{ row }">{{ formatNumber(row.coefficient) }}</template>
            </el-table-column>
            <el-table-column label="OR" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getOrTagType(row.or_value)" effect="plain">{{ formatNumber(row.or_value) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="方向" width="120" align="center">
              <template #default="{ row }">
                <span :class="getDirectionClass(row.risk_direction)">{{ row.risk_direction || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="glass-card participant-section" v-if="participants.length">
          <div class="section-title">
            <el-icon><OfficeBuilding /></el-icon>
            <span>参与机构结果摘要</span>
          </div>
          <div class="participant-grid">
            <div v-for="item in participants" :key="item.party" class="participant-card">
              <div class="participant-header">
                <h3>{{ item.district_name || item.agency_name || item.party }}</h3>
                <span>{{ item.party }}</span>
              </div>
              <div class="participant-metrics">
                <div>
                  <small>调查人数</small>
                  <strong>{{ formatInteger(item.total_count) }}</strong>
                </div>
                <div>
                  <small>高血压人数</small>
                  <strong>{{ formatInteger(item.hypertension_count) }}</strong>
                </div>
                <div>
                  <small>检出率</small>
                  <strong>{{ formatRate(item.hypertension_rate) }}</strong>
                </div>
              </div>
              <el-progress
                :percentage="toProgress(item.hypertension_rate)"
                :show-text="false"
                :stroke-width="8"
              />
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>


<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Back,
  Refresh,
  Loading,
  VideoPlay,
  DataLine,
  Histogram,
  TrendCharts,
  Warning,
  OfficeBuilding,
} from '@element-plus/icons-vue'

import { getTaskResult, runTask } from '@/api/task'
import FederatedAnimation from '@/components/FederatedAnimation.vue'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const props = defineProps<{
  task?: any
  result?: any
}>()

const refreshing = ref(false)
const running = ref(false)
const taskResult = ref<any>(null)

const districtChartRef = ref<HTMLDivElement | null>(null)
const ageChartRef = ref<HTMLDivElement | null>(null)
const genderChartRef = ref<HTMLDivElement | null>(null)
const singleChartRef = ref<HTMLDivElement | null>(null)
const interactionChartRef = ref<HTMLDivElement | null>(null)

type EChartsInstance = ReturnType<typeof echarts.init>
const districtChart = ref<EChartsInstance | null>(null)
const ageChart = ref<EChartsInstance | null>(null)
const genderChart = ref<EChartsInstance | null>(null)
const singleChart = ref<EChartsInstance | null>(null)
const interactionChart = ref<EChartsInstance | null>(null)

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

function parseJsonMaybe(value: any) {
  if (!value) return null
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch {
      return null
    }
  }
  return value
}

const sourceResult = computed(() => {
  return props.result || taskResult.value || {}
})

const resultJson = computed(() => {
  const raw =
    sourceResult.value?.result_json ??
    sourceResult.value?.result?.result_json ??
    sourceResult.value?.data?.result?.result_json ??
    sourceResult.value?.data?.result_json ??
    sourceResult.value

  return parseJsonMaybe(raw) || {}
})

const hasResult = computed(() => Object.keys(resultJson.value || {}).length > 0)
const summary = computed(() => resultJson.value.summary || {})
const participants = computed(() => resultJson.value.participants || [])
const districtStatistics = computed(() => resultJson.value.district_statistics || [])
const ageGroupStatistics = computed(() => resultJson.value.age_group_statistics || [])
const genderStatistics = computed(() => resultJson.value.gender_statistics || [])

const singleFactorRows = computed(() => {
  return (resultJson.value.single_factor_risk || []).map((row: any, index: number) => ({
    rank: row.rank || index + 1,
    ...row,
  }))
})

const interactionRows = computed(() => {
  return (resultJson.value.two_factor_interaction || []).map((row: any, index: number) => ({
    rank: row.rank || index + 1,
    ...row,
  }))
})

const regressionRows = computed(() => {
  return (resultJson.value.regression_coefficients || []).slice(0, 14)
})

const taskName = computed(() => {
  return props.task?.task_name || resultJson.value.task_name || '高血压危险因素交互作用安全分析任务'
})

const taskCodeText = computed(() => {
  return resultJson.value.task_code ? `任务编码：${resultJson.value.task_code}` : '高血压危险因素三方联合分析'
})

const riskLevelText = computed(() => {
  const rate = Number(summary.value?.hypertension_rate)
  if (!Number.isFinite(rate)) return '待评估'
  if (rate >= 0.45) return '高风险水平'
  if (rate >= 0.35) return '中高风险水平'
  return '一般风险水平'
})

const animationParties = computed(() => [
  { name: '长安区', role: '本地统计' },
  { name: '桥西区', role: '本地统计' },
  { name: '裕华区', role: '本地统计' },
])

function toNumber(value: any, fallback = 0): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function formatInteger(value: any): string {
  const n = toNumber(value, NaN)
  if (!Number.isFinite(n)) return '-'
  return Math.round(n).toLocaleString()
}

function formatNumber(value: any, digits = 3): string {
  const n = toNumber(value, NaN)
  if (!Number.isFinite(n)) return '-'
  return n.toFixed(digits).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1')
}

function formatRate(value: any): string {
  const n = toNumber(value, NaN)
  if (!Number.isFinite(n)) return '-'
  return `${(n * 100).toFixed(2)}%`
}

function toProgress(value: any): number {
  return Math.max(0, Math.min(100, Number((toNumber(value) * 100).toFixed(2))))
}

function displayPercent(row: any, rateKey: string, percentKey: string): string {
  if (row?.[percentKey] !== undefined && row?.[percentKey] !== null) {
    return `${toNumber(row[percentKey]).toFixed(2)}%`
  }
  return formatRate(row?.[rateKey])
}

function chartPercent(row: any, rateKey: string, percentKey: string): number {
  if (row?.[percentKey] !== undefined && row?.[percentKey] !== null) {
    return Number(toNumber(row[percentKey]).toFixed(2))
  }
  return Number((toNumber(row?.[rateKey]) * 100).toFixed(2))
}

function getOrTagType(value: any): 'danger' | 'warning' | 'success' | 'info' {
  const n = toNumber(value)
  if (n >= 2) return 'danger'
  if (n >= 1.25) return 'warning'
  if (n > 0 && n <= 0.8) return 'success'
  return 'info'
}

function getDirectionClass(value: string): string {
  if (value?.includes('升高')) return 'risk-up'
  if (value?.includes('降低')) return 'risk-down'
  return 'risk-flat'
}

function ensureChart(chartRef: typeof districtChart, domRef: typeof districtChartRef) {
  if (!domRef.value) return null
  if (!chartRef.value) {
    chartRef.value = echarts.init(domRef.value)
  }
  return chartRef.value
}

function renderDistrictChart() {
  if (!districtStatistics.value.length) return
  const chart = ensureChart(districtChart, districtChartRef)
  if (!chart) return

  const names = districtStatistics.value.map((item: any) => item.district_name || item.agency_name || item.party)
  const values = districtStatistics.value.map((item: any) => chartPercent(item, 'hypertension_rate', 'hypertension_rate_percent'))

  chart.setOption({
    color: ['#409EFF'],
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => `${v}%` },
    grid: { left: 44, right: 18, top: 28, bottom: 36 },
    xAxis: { type: 'category', data: names, axisTick: { show: false }, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: '检出率', axisLabel: { formatter: '{value}%', color: '#6f7f95' } },
    series: [
      {
        name: '检出率',
        type: 'bar',
        barMaxWidth: 38,
        label: { show: true, position: 'top', formatter: '{c}%' },
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        data: values,
      },
    ],
  })
}

function renderAgeChart() {
  if (!ageGroupStatistics.value.length) return
  const chart = ensureChart(ageChart, ageChartRef)
  if (!chart) return

  const names = ageGroupStatistics.value.map((item: any) => item.age_group)
  const values = ageGroupStatistics.value.map((item: any) => chartPercent(item, 'hypertension_rate', 'hypertension_rate_percent'))

  chart.setOption({
    color: ['#F6A623'],
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => `${v}%` },
    grid: { left: 44, right: 18, top: 28, bottom: 36 },
    xAxis: { type: 'category', data: names, axisTick: { show: false }, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: '检出率', axisLabel: { formatter: '{value}%', color: '#6f7f95' } },
    series: [
      {
        name: '检出率',
        type: 'line',
        smooth: true,
        symbolSize: 8,
        label: { show: true, position: 'top', formatter: '{c}%' },
        lineStyle: { width: 3 },
        areaStyle: { color: 'rgba(246, 166, 35, 0.12)' },
        data: values,
      },
    ],
  })
}

function renderGenderChart() {
  if (!genderStatistics.value.length) return
  const chart = ensureChart(genderChart, genderChartRef)
  if (!chart) return

  const names = genderStatistics.value.map((item: any) => item.gender === 'M' ? '男性' : item.gender === 'F' ? '女性' : item.gender)
  const values = genderStatistics.value.map((item: any) => chartPercent(item, 'hypertension_rate', 'hypertension_rate_percent'))

  chart.setOption({
    color: ['#36CFC9'],
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => `${v}%` },
    grid: { left: 44, right: 18, top: 28, bottom: 36 },
    xAxis: { type: 'category', data: names, axisTick: { show: false }, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: '检出率', axisLabel: { formatter: '{value}%', color: '#6f7f95' } },
    series: [
      {
        name: '检出率',
        type: 'bar',
        barMaxWidth: 42,
        label: { show: true, position: 'top', formatter: '{c}%' },
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        data: values,
      },
    ],
  })
}

function renderSingleChart() {
  if (!singleFactorRows.value.length) return
  const chart = ensureChart(singleChart, singleChartRef)
  if (!chart) return

  const rows = singleFactorRows.value.slice(0, 8).reverse()
  chart.setOption({
    color: ['#FF6B6B'],
    tooltip: { trigger: 'axis' },
    grid: { left: 94, right: 26, top: 18, bottom: 28 },
    xAxis: { type: 'value', axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'category', data: rows.map((x: any) => x.factor_name), axisTick: { show: false }, axisLabel: { color: '#6f7f95' } },
    series: [
      {
        name: 'OR',
        type: 'bar',
        label: { show: true, position: 'right' },
        itemStyle: { borderRadius: [0, 8, 8, 0] },
        data: rows.map((x: any) => toNumber(x.or_value)),
      },
    ],
  })
}

function renderInteractionChart() {
  if (!interactionRows.value.length) return
  const chart = ensureChart(interactionChart, interactionChartRef)
  if (!chart) return

  const rows = interactionRows.value.slice(0, 8).reverse()
  chart.setOption({
    color: ['#69B8FF'],
    tooltip: { trigger: 'axis' },
    grid: { left: 132, right: 26, top: 18, bottom: 28 },
    xAxis: { type: 'value', axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'category', data: rows.map((x: any) => x.interaction_name), axisTick: { show: false }, axisLabel: { color: '#6f7f95' } },
    series: [
      {
        name: 'OR',
        type: 'bar',
        label: { show: true, position: 'right' },
        itemStyle: { borderRadius: [0, 8, 8, 0] },
        data: rows.map((x: any) => toNumber(x.or_value)),
      },
    ],
  })
}

async function renderCharts() {
  await nextTick()
  if (running.value || !hasResult.value) return
  renderDistrictChart()
  renderAgeChart()
  renderGenderChart()
  renderSingleChart()
  renderInteractionChart()
}

function resizeCharts() {
  districtChart.value?.resize()
  ageChart.value?.resize()
  genderChart.value?.resize()
  singleChart.value?.resize()
  interactionChart.value?.resize()
}

function disposeCharts() {
  districtChart.value?.dispose()
  ageChart.value?.dispose()
  genderChart.value?.dispose()
  singleChart.value?.dispose()
  interactionChart.value?.dispose()
  districtChart.value = null
  ageChart.value = null
  genderChart.value = null
  singleChart.value = null
  interactionChart.value = null
}

async function loadResult() {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
    disposeCharts()
    await renderCharts()
  } catch {
    taskResult.value = null
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    await loadResult()
  } finally {
    refreshing.value = false
  }
}

function goDetail() {
  router.push(`/tasks/${taskId}`)
}

async function handleAutoRun() {
  taskResult.value = null
  disposeCharts()
  running.value = true

  const minAnimationTime = 5000
  const startTime = Date.now()

  try {
    await runTask(taskId)
    ElMessage.success('任务执行成功')
    await loadResult()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || '任务执行失败'
    ElMessage.error(detail)
  } finally {
    const elapsed = Date.now() - startTime
    const remainingTime = Math.max(0, minAnimationTime - elapsed)
    if (remainingTime > 0) {
      await new Promise((resolve) => setTimeout(resolve, remainingTime))
    }
    running.value = false
    await renderCharts()
  }
}

watch(resultJson, () => {
  disposeCharts()
  renderCharts()
}, { deep: true })

onMounted(async () => {
  window.addEventListener('resize', resizeCharts)

  if (props.result) {
    await renderCharts()
    return
  }

  if (route.query.autoRun === '1') {
    await handleAutoRun()
  } else {
    await refreshAll()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
</script>

<style scoped>
.t4-result-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at 12% 8%, rgba(64, 158, 255, 0.12), transparent 28%),
    radial-gradient(circle at 82% 12%, rgba(54, 207, 201, 0.10), transparent 30%),
    linear-gradient(135deg, #f3f9ff 0%, #eef6ff 100%);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.title-area h1 {
  margin: 0 0 8px;
  color: #1f2f4d;
  font-size: 24px;
  font-weight: 800;
}

.title-area p {
  margin: 0;
  color: #6f7f95;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.glass-card {
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 36px rgba(31, 45, 61, 0.08);
  backdrop-filter: blur(12px);
}

.running-card,
.overview-main,
.interpretation-card,
.chart-card,
.table-card,
.participant-section {
  padding: 24px;
}

.result-header,
.overview-title,
.section-title,
.participant-header {
  display: flex;
  align-items: center;
}

.result-header {
  justify-content: space-between;
  margin-bottom: 20px;
}

.card-title,
.section-title {
  gap: 8px;
  color: #273b5a;
  font-weight: 800;
}

.section-title {
  margin-bottom: 18px;
  font-size: 17px;
}

.section-title.compact {
  margin-bottom: 12px;
}

.empty-result {
  min-height: 420px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
}

.running-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 12px;
  color: #d48806;
  background: #fffaf0;
}

.overview-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 22px;
}

.overview-title {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.overview-title h2 {
  margin: 0 0 8px;
  color: #1f2f4d;
  font-size: 22px;
  font-weight: 800;
}

.overview-title p,
.interpretation-item p,
.chart-note {
  margin: 0;
  color: #6f7f95;
  line-height: 1.7;
}

.risk-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  padding: 8px 14px;
  border-radius: 999px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  background: linear-gradient(135deg, #409eff, #36cfc9);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f7fbff, #ffffff);
  border: 1px solid #e8f1fb;
}

.metric-card.blue {
  background: linear-gradient(180deg, #f1f7ff, #ffffff);
}

.metric-card.danger {
  background: linear-gradient(180deg, #fff4f4, #ffffff);
}

.metric-card.warning {
  background: linear-gradient(180deg, #fff8eb, #ffffff);
}

.metric-card.cyan {
  background: linear-gradient(180deg, #effefd, #ffffff);
}

.metric-card.purple {
  background: linear-gradient(180deg, #f6f3ff, #ffffff);
}

.metric-card.sky {
  background: linear-gradient(180deg, #eef8ff, #ffffff);
}

.metric-label,
.metric-card span {
  display: block;
  margin-bottom: 8px;
  color: #7a8aa0;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  color: #1f2f4d;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 26px;
  line-height: 1.12;
}

.metric-card small {
  display: block;
  margin-top: 8px;
  color: #98a2b3;
}

.metric-card .text-fit {
  min-height: 32px;
  font-family: inherit;
  font-size: 20px;
}

.interpretation-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.interpretation-item {
  padding: 14px;
  border-radius: 14px;
  background: #f7fbff;
  border: 1px solid #e8f1fb;
}

.interpretation-item .el-tag {
  margin-bottom: 8px;
}

.chart-grid,
.table-grid {
  display: grid;
  gap: 22px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-box {
  height: 320px;
}

.wide-chart-box {
  height: 360px;
}

.chart-note {
  margin-top: -6px;
  font-size: 12px;
}

.table-title {
  justify-content: space-between;
}

.rate-strong {
  color: #1f2f4d;
  font-weight: 800;
}

.rate-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.risk-up {
  color: #d92d20;
  font-weight: 800;
}

.risk-down {
  color: #039855;
  font-weight: 800;
}

.risk-flat {
  color: #667085;
  font-weight: 700;
}

.participant-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.participant-card {
  padding: 18px;
  border: 1px solid #e8f1fb;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbff, #ffffff);
}

.participant-header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.participant-header h3 {
  margin: 0;
  color: #1f2f4d;
  font-size: 17px;
  font-weight: 800;
}

.participant-header span {
  padding: 4px 10px;
  border-radius: 999px;
  color: #409eff;
  background: #eef6ff;
  font-size: 12px;
  font-weight: 800;
}

.participant-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.participant-metrics div {
  padding: 12px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #edf3fa;
}

.participant-metrics small {
  display: block;
  margin-bottom: 6px;
  color: #7a8aa0;
  font-size: 12px;
}

.participant-metrics strong {
  color: #1f2f4d;
  font-size: 18px;
}

:deep(.pretty-table) {
  border-radius: 14px;
  overflow: hidden;
}

:deep(.pretty-table .el-table__header th) {
  background: #f7fbff !important;
  color: #344054;
  font-weight: 800;
}

:deep(.pretty-table .el-table__row:hover > td) {
  background: #f5faff !important;
}

:deep(.pretty-table .el-table__cell) {
  padding: 9px 0;
}

@media (max-width: 1280px) {
  .overview-section,
  .two-columns,
  .participant-grid {
    grid-template-columns: 1fr;
  }

  .metric-grid {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }
}

@media (max-width: 768px) {
  .t4-result-page {
    padding: 16px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid,
  .participant-metrics {
    grid-template-columns: 1fr;
  }
}


</style>
