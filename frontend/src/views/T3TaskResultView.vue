<template>
  <div class="t3-result-page">
    <header class="page-header">
      <div class="title-area">
        <h1>疫苗效果评估结果</h1>
        <p>展示总体 VE、接种状态差异、区县差异、年龄段差异和每日阳性率趋势</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Back" @click="goDetail">返回详情</el-button>
        <el-button :icon="Refresh" :loading="refreshing" @click="refreshAll">刷新结果</el-button>
      </div>
    </header>

    <main class="page-content">
      <div v-if="running" class="glass-card running-card">
        <div class="result-header">
          <span class="card-title"><el-icon><VideoPlay /></el-icon> 疫苗效果评估执行中</span>
          <el-tag type="warning" effect="dark">执行中</el-tag>
        </div>

        <FederatedAnimation :parties="animationParties" :total-rounds="8" task-name="疫苗安全效果持续评估任务" />

        <div class="running-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在执行三方联合统计与疫苗保护效果计算，请稍候...</span>
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
                <h2>{{ regionName }}疫苗效果评估</h2>
                <p>{{ taskCodeText }}</p>
              </div>
              <span :class="['ve-pill', veLevelClass]">{{ veLevelText }}</span>
            </div>

            <div class="metric-grid">
              <div class="metric-card ve-card">
                <span class="metric-label">总体 VE</span>
                <strong>{{ formatPercentValue(overallVe) }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">总检测人数</span>
                <strong>{{ summary?.total_count || 0 }}</strong>
              </div>
              <div class="metric-card danger">
                <span class="metric-label">阳性人数</span>
                <strong>{{ summary?.positive_count || 0 }}</strong>
              </div>
              <div class="metric-card warning">
                <span class="metric-label">总体阳性率</span>
                <strong>{{ formatRate(summary?.positive_rate) }}</strong>
              </div>
              <div class="metric-card purple">
                <span class="metric-label">接种率</span>
                <strong>{{ formatRate(summary?.vaccination_rate) }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">参与机构</span>
                <strong>{{ participants.length }}</strong>
              </div>
            </div>
          </div>

          <div class="interpretation-card glass-card">
            <div class="section-title compact">
              <el-icon><Warning /></el-icon>
              <span>评估结论</span>
            </div>
            <div v-if="riskInterpretation.length" class="interpretation-list">
              <div
                v-for="item in riskInterpretation"
                :key="item.title"
                class="interpretation-item"
              >
                <el-tag :type="getRiskTagType(item.level)" effect="light" size="small">
                  {{ item.title || '提示' }}
                </el-tag>
                <p>{{ item.content }}</p>
              </div>
            </div>
            <p v-else class="muted-text">暂无自动解读，建议结合区县和年龄段分层结果继续分析。</p>
          </div>
        </section>

        <section class="chart-grid two-columns">
          <div class="glass-card chart-card" v-if="overallEffect">
            <div class="section-title">
              <el-icon><DataLine /></el-icon>
              <span>接种状态阳性率对比</span>
            </div>
            <div ref="positiveCompareChartRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-card" v-if="districtEffect.length">
            <div class="section-title">
              <el-icon><Histogram /></el-icon>
              <span>区县疫苗保护效果对比</span>
            </div>
            <div ref="districtChartRef" class="chart-box"></div>
          </div>
        </section>

        <section class="chart-grid two-columns">
          <div class="glass-card chart-card" v-if="ageGroupEffect.length">
            <div class="section-title">
              <el-icon><TrendCharts /></el-icon>
              <span>年龄段保护效果分析</span>
            </div>
            <div ref="ageChartRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-card" v-if="vaccinationWindowEffect.length">
            <div class="section-title">
              <el-icon><PieChart /></el-icon>
              <span>接种时间窗口阳性率</span>
            </div>
            <div ref="windowChartRef" class="chart-box"></div>
            <div class="chart-note">该图展示不同接种时间窗口内的阳性率变化，不直接计算 VE。</div>
          </div>
        </section>

        <section class="glass-card chart-card" v-if="dailyTrend.length">
          <div class="section-title">
            <el-icon><TrendCharts /></el-icon>
            <span>每日阳性率趋势</span>
          </div>
          <div ref="trendChartRef" class="wide-chart-box"></div>
        </section>

        <section class="glass-card participant-section" v-if="participants.length">
          <div class="section-title">
            <el-icon><OfficeBuilding /></el-icon>
            <span>参与机构结果摘要</span>
          </div>
          <div class="participant-grid">
            <div v-for="item in participants" :key="item.party" class="participant-card">
              <div class="participant-header">
                <h3>{{ shortDistrictName(item.district_name || item.party_name) }}</h3>
                <span>{{ item.party }}</span>
              </div>
              <div class="participant-metrics">
                <div>
                  <small>检测人数</small>
                  <strong>{{ item.total_count || 0 }}</strong>
                </div>
                <div>
                  <small>阳性人数</small>
                  <strong>{{ item.positive_count || 0 }}</strong>
                </div>
                <div>
                  <small>阳性率</small>
                  <strong>{{ formatRate(calcParticipantPositiveRate(item)) }}</strong>
                </div>
              </div>
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
  DataLine,
  TrendCharts,
  Warning,
  Loading,
  VideoPlay,
  Histogram,
  PieChart,
  OfficeBuilding,
} from '@element-plus/icons-vue'

import { getTaskResult, runTask } from '@/api/task'
import FederatedAnimation from '@/components/FederatedAnimation.vue'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const refreshing = ref(false)
const running = ref(false)
const taskResult = ref<any>(null)

const positiveCompareChartRef = ref<HTMLDivElement | null>(null)
const districtChartRef = ref<HTMLDivElement | null>(null)
const ageChartRef = ref<HTMLDivElement | null>(null)
const windowChartRef = ref<HTMLDivElement | null>(null)
const trendChartRef = ref<HTMLDivElement | null>(null)

type EChartsInstance = ReturnType<typeof echarts.init>

const positiveCompareChart = ref<EChartsInstance | null>(null)
const districtChart = ref<EChartsInstance | null>(null)
const ageChart = ref<EChartsInstance | null>(null)
const windowChart = ref<EChartsInstance | null>(null)
const trendChart = ref<EChartsInstance | null>(null)

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

const resultJson = computed(() => {
  const raw = taskResult.value?.result_json ?? taskResult.value?.result ?? taskResult.value
  return parseJsonMaybe(raw) || {}
})

const hasResult = computed(() => Object.keys(resultJson.value || {}).length > 0)
const summary = computed(() => resultJson.value.summary || null)
const overallEffect = computed(() => resultJson.value.overall_effect || null)
const districtEffect = computed(() => resultJson.value.district_effect || [])
const ageGroupEffect = computed(() => resultJson.value.age_group_effect || [])
const vaccinationWindowEffect = computed(() => resultJson.value.vaccination_window_effect || [])
const dailyTrend = computed(() => resultJson.value.daily_trend || [])
const participants = computed(() => resultJson.value.participants || [])
const riskInterpretation = computed(() => resultJson.value.risk_interpretation || [])

const regionName = computed(() => resultJson.value.region_name || '石家庄市')
const taskCodeText = computed(() => resultJson.value.task_code ? `任务编码：${resultJson.value.task_code}` : '疫苗接种与检测数据联合评估')
const overallVe = computed(() => summary.value?.overall_ve ?? overallEffect.value?.ve_value ?? null)

const veLevelText = computed(() => {
  const value = Number(overallVe.value)
  if (Number.isNaN(value)) return '样本不足'
  if (value >= 50) return '保护效果较明显'
  if (value >= 20) return '保护效果中等'
  return '保护效果偏弱'
})

const veLevelClass = computed(() => {
  const value = Number(overallVe.value)
  if (Number.isNaN(value)) return 'unknown'
  if (value >= 50) return 'good'
  if (value >= 20) return 'normal'
  return 'weak'
})

const animationParties = computed(() => [
  { name: '长安区', role: '数据统计' },
  { name: '桥西区', role: '数据统计' },
  { name: '裕华区', role: '数据统计' },
])

function shortDistrictName(name: string) {
  if (!name) return '-'
  return name
    .replace('河北省石家庄市', '')
    .replace('石家庄市', '')
    .replace('河北省', '')
}

function formatRate(value: any) {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return '-'
  return `${(num * 100).toFixed(2)}%`
}

function formatPercentValue(value: any) {
  if (value === null || value === undefined) return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return '-'
  return `${num.toFixed(2)}%`
}

function toRatePercent(value: any) {
  const num = Number(value)
  return Number.isNaN(num) ? 0 : Number((num * 100).toFixed(2))
}

function toPercentValue(value: any) {
  const num = Number(value)
  return Number.isNaN(num) ? 0 : Number(num.toFixed(2))
}

function calcParticipantPositiveRate(item: any) {
  const total = Number(item.total_count || 0)
  if (!total) return null
  return Number(item.positive_count || 0) / total
}

function getRiskTagType(level: string) {
  const map: Record<string, string> = {
    positive: 'success',
    normal: 'primary',
    warning: 'warning',
    danger: 'danger',
  }
  return map[level] || 'primary'
}

function ensureChart(chartRef: typeof positiveCompareChart, domRef: typeof positiveCompareChartRef) {
  if (!domRef.value) return null
  if (!chartRef.value) {
    chartRef.value = echarts.init(domRef.value)
  }
  return chartRef.value
}

function renderPositiveCompareChart() {
  if (!overallEffect.value) return
  const chart = ensureChart(positiveCompareChart, positiveCompareChartRef)
  if (!chart) return

  chart.setOption({
    color: ['#409EFF', '#FF6B6B'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        return params.map((p) => `${p.marker}${p.name}：${p.value}%`).join('<br/>')
      },
    },
    grid: { left: 42, right: 20, top: 32, bottom: 36 },
    xAxis: {
      type: 'category',
      data: ['接种组', '未接种组'],
    },
    yAxis: {
      type: 'value',
      name: '阳性率',
      axisLabel: { formatter: '{value}%', color: '#6f7f95' },
    },
    series: [
      {
        name: '阳性率',
        type: 'bar',
        barMaxWidth: 52,
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
        },
        data: [
          {
            value: toRatePercent(overallEffect.value.vaccinated_positive_rate),
            itemStyle: { color: '#409EFF' },
          },
          {
            value: toRatePercent(overallEffect.value.unvaccinated_positive_rate),
            itemStyle: { color: '#FF6B6B' },
          },
        ],
      },
    ],
  })
}

function renderDistrictChart() {
  if (!districtEffect.value.length) return
  const chart = ensureChart(districtChart, districtChartRef)
  if (!chart) return

  const names = districtEffect.value.map((item: any) => shortDistrictName(item.district_name))
  const veValues = districtEffect.value.map((item: any) => {
    const value = toPercentValue(item.ve_value)
    return {
      value,
      itemStyle: {
        color: value >= 50 ? '#409EFF' : value >= 40 ? '#69B8FF' : '#F6A623',
      },
    }
  })

  chart.setOption({
    color: ['#69B8FF'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        const p = params[0]
        const raw = districtEffect.value[p.dataIndex]
        return [
          `<strong>${shortDistrictName(raw.district_name)}</strong>`,
          `VE：${formatPercentValue(raw.ve_value)}`,
          `检测人数：${raw.total_count || 0}`,
          `阳性率：${formatRate(raw.positive_rate)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 42, right: 20, top: 32, bottom: 36 },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: 'VE', axisLabel: { formatter: '{value}%', color: '#6f7f95' }, max: 100 },
    series: [
      {
        name: 'VE',
        type: 'bar',
        barMaxWidth: 36,
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}%' },
        data: veValues,
      },
    ],
  })
}

function renderAgeChart() {
  if (!ageGroupEffect.value.length) return
  const chart = ensureChart(ageChart, ageChartRef)
  if (!chart) return

  const names = ageGroupEffect.value.map((item: any) => item.age_group)
  const veValues = ageGroupEffect.value.map((item: any) => {
    const value = toPercentValue(item.ve_value)
    return {
      value,
      itemStyle: {
        color: value >= 60 ? '#409EFF' : value >= 45 ? '#69B8FF' : '#F6A623',
      },
    }
  })

  chart.setOption({
    color: ['#69B8FF'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        const p = params[0]
        const raw = ageGroupEffect.value[p.dataIndex]
        return [
          `<strong>${raw.age_group}</strong>`,
          `VE：${formatPercentValue(raw.ve_value)}`,
          `接种组阳性率：${formatRate(raw.vaccinated_positive_rate)}`,
          `未接种组阳性率：${formatRate(raw.unvaccinated_positive_rate)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 42, right: 20, top: 32, bottom: 36 },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: 'VE', axisLabel: { formatter: '{value}%', color: '#6f7f95' }, max: 100 },
    series: [
      {
        name: 'VE',
        type: 'bar',
        barMaxWidth: 36,
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}%' },
        data: veValues,
      },
    ],
  })
}

function renderWindowChart() {
  if (!vaccinationWindowEffect.value.length) return
  const chart = ensureChart(windowChart, windowChartRef)
  if (!chart) return

  const names = vaccinationWindowEffect.value.map((item: any) => item.vaccination_window)
  const rates = vaccinationWindowEffect.value.map((item: any) => {
    const value = toRatePercent(item.positive_rate)
    return {
      value,
      itemStyle: {
        color: value >= 14 ? '#F6A623' : value >= 11 ? '#69B8FF' : '#36CFC9',
      },
    }
  })

  chart.setOption({
    color: ['#73B7E8'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        const p = params[0]
        const raw = vaccinationWindowEffect.value[p.dataIndex]
        return [
          `<strong>${raw.vaccination_window} 天</strong>`,
          `阳性率：${formatRate(raw.positive_rate)}`,
          `样本数：${raw.total_count || 0}`,
          `阳性数：${raw.positive_count || 0}`,
        ].join('<br/>')
      },
    },
    grid: { left: 42, right: 20, top: 32, bottom: 36 },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: '阳性率', axisLabel: { formatter: '{value}%', color: '#6f7f95' } },
    series: [
      {
        name: '阳性率',
        type: 'bar',
        barMaxWidth: 36,
        itemStyle: { borderRadius: [8, 8, 0, 0] },
        label: { show: true, position: 'top', formatter: '{c}%' },
        data: rates,
      },
    ],
  })
}

function renderTrendChart() {
  if (!dailyTrend.value.length) return
  const chart = ensureChart(trendChart, trendChartRef)
  if (!chart) return

  const dates = dailyTrend.value.map((item: any) => item.date?.slice(5) || item.date)
  const overallRates = dailyTrend.value.map((item: any) => toRatePercent(item.positive_rate))
  const vaccinatedRates = dailyTrend.value.map((item: any) => toRatePercent(item.vaccinated_positive_rate))
  const unvaccinatedRates = dailyTrend.value.map((item: any) => toRatePercent(item.unvaccinated_positive_rate))

  chart.setOption({
    color: ['#409EFF', '#36CFC9', '#FF6B6B'],
    tooltip: {
      trigger: 'axis',
      formatter(params: any[]) {
        const rows = params.map((p) => `${p.marker}${p.seriesName}：${p.value}%`)
        return `${params[0]?.axisValue || ''}<br/>${rows.join('<br/>')}`
      },
    },
    legend: { top: 0, data: ['总体阳性率', '接种组阳性率', '未接种组阳性率'] },
    grid: { left: 42, right: 30, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel: { color: '#6f7f95' } },
    yAxis: { type: 'value', name: '阳性率', axisLabel: { formatter: '{value}%', color: '#6f7f95' } },
    series: [
      {
        name: '总体阳性率',
        type: 'line',
        smooth: true,
        symbolSize: 5,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(77, 163, 255, 0.22)' },
            { offset: 1, color: 'rgba(77, 163, 255, 0.05)' },
          ]),
        },
        data: overallRates,
      },
      {
        name: '接种组阳性率',
        type: 'line',
        smooth: true,
        symbolSize: 5,
        data: vaccinatedRates,
      },
      {
        name: '未接种组阳性率',
        type: 'line',
        smooth: true,
        symbolSize: 5,
        lineStyle: { type: 'dashed' },
        data: unvaccinatedRates,
      },
    ],
  })
}

async function renderCharts() {
  await nextTick()
  if (running.value || !hasResult.value) return
  renderPositiveCompareChart()
  renderDistrictChart()
  renderAgeChart()
  renderWindowChart()
  renderTrendChart()
}

function resizeCharts() {
  positiveCompareChart.value?.resize()
  districtChart.value?.resize()
  ageChart.value?.resize()
  windowChart.value?.resize()
  trendChart.value?.resize()
}

function disposeCharts() {
  positiveCompareChart.value?.dispose()
  districtChart.value?.dispose()
  ageChart.value?.dispose()
  windowChart.value?.dispose()
  trendChart.value?.dispose()
  positiveCompareChart.value = null
  districtChart.value = null
  ageChart.value = null
  windowChart.value = null
  trendChart.value = null
}

async function loadResult() {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
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
  renderCharts()
}, { deep: true })

onMounted(async () => {
  window.addEventListener('resize', resizeCharts)

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
.t3-result-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at 12% 8%, rgba(91, 143, 185, 0.14), transparent 28%),
    radial-gradient(circle at 82% 12%, rgba(90, 169, 157, 0.10), transparent 30%),
    linear-gradient(135deg, #f3f9ff 0%, #eaf5ff 100%);
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
  font-weight: 700;
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
  gap: 24px;
}

.glass-card {
  border: 1px solid rgba(255, 255, 255, 0.68);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 36px rgba(31, 45, 61, 0.08);
  backdrop-filter: blur(12px);
}

.running-card,
.overview-main,
.interpretation-card,
.chart-card,
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
  font-weight: 700;
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
  background: rgba(255, 255, 255, 0.75);
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
  gap: 24px;
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
  font-weight: 750;
}

.overview-title p,
.muted-text,
.chart-note,
.interpretation-item p {
  margin: 0;
  color: #6f7f95;
  line-height: 1.7;
}

.ve-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  padding: 8px 14px;
  border-radius: 999px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  background: linear-gradient(135deg, #409EFF, #36CFC9);
}

.ve-pill.good {
  background: linear-gradient(135deg, #36CFC9, #73D6FF);
}

.ve-pill.normal {
  background: linear-gradient(135deg, #409EFF, #73B7E8);
}

.ve-pill.weak,
.ve-pill.unknown {
  background: linear-gradient(135deg, #F6A623, #FFB86B);
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

.metric-card.ve-card {
  background: linear-gradient(180deg, #f5fbff, #ffffff);
  border-color: #d9ecff;
}

.metric-card.danger {
  background: linear-gradient(180deg, #fff7f7, #ffffff);
  border-color: #ffd8d8;
}

.metric-card.warning {
  background: linear-gradient(180deg, #fffaf2, #ffffff);
  border-color: #ffe8c7;
}

.metric-card.purple {
  background: linear-gradient(180deg, #f6fbff, #ffffff);
  border-color: #d9ecff;
}

.metric-label {
  display: block;
  margin-bottom: 10px;
  color: #7f8fa6;
  font-size: 13px;
}

.metric-card strong {
  color: #1f2f4d;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 30px;
  line-height: 1;
}

.interpretation-card {
  min-height: 100%;
}

.interpretation-list {
  display: grid;
  gap: 12px;
}

.interpretation-item {
  padding: 12px 14px;
  border-radius: 12px;
  background: #f7f9fc;
}

.interpretation-item p {
  margin-top: 8px;
  font-size: 13px;
}

.chart-grid {
  display: grid;
  gap: 24px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-box {
  height: 340px;
}

.wide-chart-box {
  height: 380px;
}

.chart-note {
  margin-top: 8px;
  font-size: 12px;
}

.participant-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.participant-card {
  padding: 18px;
  border: 1px solid #edf1f7;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff, #ffffff);
}

.participant-header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.participant-header h3 {
  margin: 0;
  color: #273b5a;
  font-size: 16px;
  font-weight: 700;
}

.participant-header span {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  color: #409EFF;
  background: #f5fbff;
  font-size: 12px;
  font-weight: 700;
}

.participant-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.participant-metrics div {
  padding: 10px;
  border-radius: 12px;
  background: #f7f9fc;
}

.participant-metrics small {
  display: block;
  margin-bottom: 6px;
  color: #8a98aa;
  font-size: 12px;
}

.participant-metrics strong {
  color: #1f2f4d;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 20px;
}

@media (max-width: 1400px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .overview-section {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1080px) {
  .two-columns,
  .participant-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .t3-result-page {
    padding: 16px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .metric-grid,
  .participant-metrics {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
