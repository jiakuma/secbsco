<template>
  <div class="t2-result-page">
    <header class="page-header">
      <div class="title-area">
        <h1>疫情时空分析结果</h1>
        <p>仅展示病例趋势、区县对比、空间风险、共同暴露等数据分析结果</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Back" @click="goDetail">返回详情</el-button>
        <el-button :icon="Refresh" :loading="refreshing" @click="refreshAll">刷新结果</el-button>
      </div>
    </header>

    <main class="page-content">
      <div v-if="running" class="glass-card running-card">
        <div class="result-header">
          <span class="card-title"><el-icon><VideoPlay /></el-icon> 数据分析执行中</span>
          <el-tag type="warning" effect="dark">执行中</el-tag>
        </div>

        <FederatedAnimation :parties="animationParties" :total-rounds="10" />

        <div class="running-tip">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在执行跨区县数据分析，请稍候...</span>
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
                <h2>{{ diseaseName }}时空分析结果</h2>
                <p>{{ analysisPeriodText }}</p>
              </div>
              <span :class="['trend-pill', prediction?.trend_level === 'rising' ? 'rising' : 'stable']">
                {{ trendLevelText }}
              </span>
            </div>

            <div class="metric-grid">
              <div class="metric-card">
                <span class="metric-label">总病例数</span>
                <strong>{{ summary?.total_case_count || 0 }}</strong>
              </div>
              <div class="metric-card danger">
                <span class="metric-label">阳性数</span>
                <strong>{{ summary?.total_positive_count || 0 }}</strong>
              </div>
              <div class="metric-card warning">
                <span class="metric-label">总体阳性率</span>
                <strong>{{ formatRate(summary?.overall_positive_rate) }}</strong>
              </div>
              <div class="metric-card">
                <span class="metric-label">高风险网格</span>
                <strong>{{ summary?.high_risk_grid_count || highRiskGrids.length || 0 }}</strong>
              </div>
              <div class="metric-card purple">
                <span class="metric-label">共同暴露区域</span>
                <strong>{{ summary?.common_exposure_grid_count || commonExposureAnalysis.length || 0 }}</strong>
              </div>
              <div class="metric-card danger-light">
                <span class="metric-label">未来{{ prediction?.prediction_window_days || 7 }}日预测病例</span>
                <strong>{{ prediction?.predicted_total_case_count || 0 }}</strong>
              </div>
            </div>
          </div>

          <div class="prediction-card glass-card" v-if="prediction">
            <div class="section-title compact">
              <el-icon><Warning /></el-icon>
              <span>趋势研判</span>
            </div>
            <p class="prediction-message">{{ prediction.message || '暂无预测说明' }}</p>
            <div class="prediction-list" v-if="districtPredictions.length">
              <div v-for="item in districtPredictions" :key="item.district_code || item.district_name" class="prediction-item">
                <div>
                  <span>{{ shortDistrictName(item.district_name) }}</span>
                  <small>{{ getRiskLevelText(item.risk_level) }}</small>
                </div>
                <strong>{{ item.predicted_case_count || 0 }}</strong>
              </div>
            </div>
          </div>
        </section>

        <section class="chart-grid two-columns">
          <div class="glass-card chart-card" v-if="dailyTrend.length">
            <div class="section-title">
              <el-icon><TrendCharts /></el-icon>
              <span>每日病例趋势</span>
            </div>
            <div ref="trendChartRef" class="chart-box"></div>
          </div>

          <div class="glass-card chart-card" v-if="districtStatistics.length">
            <div class="section-title">
              <el-icon><DataLine /></el-icon>
              <span>区县病例对比</span>
            </div>
            <div ref="districtChartRef" class="chart-box"></div>
          </div>
        </section>

        <section class="chart-grid map-layout" v-if="highRiskGrids.length">
          <div class="glass-card chart-card map-card">
            <div class="section-title">
              <el-icon><Location /></el-icon>
              <span>高风险网格空间分布</span>
            </div>
            <div ref="riskMapChartRef" class="map-chart-box"></div>
            <div class="map-note">
              当前使用网格中心经纬度绘制空间散点图；如后续提供石家庄/区县 GeoJSON，可升级为真实行政区划地图。
            </div>
          </div>

          <div class="glass-card chart-card rank-card">
            <div class="section-title">
              <el-icon><Warning /></el-icon>
              <span>高风险网格排行</span>
            </div>
            <div ref="riskRankChartRef" class="rank-chart-box"></div>
          </div>
        </section>

        <section class="glass-card exposure-section" v-if="commonExposureAnalysis.length">
          <div class="section-title">
            <el-icon><Connection /></el-icon>
            <span>共同暴露区域</span>
          </div>

          <div class="exposure-grid">
            <div
              v-for="item in topCommonExposure"
              :key="item.grid_id || item.grid_name"
              class="exposure-card"
            >
              <div class="exposure-header">
                <h3>{{ item.grid_name }}</h3>
                <span class="exposure-type">{{ getPlaceTypeText(item.place_type) }}</span>
              </div>
              <div class="exposure-metrics">
                <div>
                  <span>暴露病例</span>
                  <strong>{{ item.exposed_case_count || 0 }}</strong>
                </div>
                <div>
                  <span>阳性数</span>
                  <strong>{{ item.positive_count || 0 }}</strong>
                </div>
                <div>
                  <span>阳性率</span>
                  <strong>{{ formatRate(item.positive_rate) }}</strong>
                </div>
              </div>
              <p class="risk-reason">{{ item.risk_reason || '近 14 日病例暴露频次较高，建议结合流调信息复核。' }}</p>
              <div class="district-tags" v-if="item.involved_districts?.length">
                <el-tag
                  v-for="district in item.involved_districts"
                  :key="district"
                  size="small"
                  effect="plain"
                >
                  {{ shortDistrictName(district) }}
                </el-tag>
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
  Connection,
  TrendCharts,
  Location,
  Warning,
  Loading,
  VideoPlay,
} from '@element-plus/icons-vue'

import { getTaskResult, runTask } from '@/api/task'
import FederatedAnimation from '@/components/FederatedAnimation.vue'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const refreshing = ref(false)
const running = ref(false)
const taskResult = ref<any>(null)

const trendChartRef = ref<HTMLDivElement | null>(null)
const districtChartRef = ref<HTMLDivElement | null>(null)
const riskMapChartRef = ref<HTMLDivElement | null>(null)
const riskRankChartRef = ref<HTMLDivElement | null>(null)

type EChartsInstance = ReturnType<typeof echarts.init>

const trendChart = ref<EChartsInstance | null>(null)
const districtChart = ref<EChartsInstance | null>(null)
const riskMapChart = ref<EChartsInstance | null>(null)
const riskRankChart = ref<EChartsInstance | null>(null)

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
const districtStatistics = computed(() => resultJson.value.district_statistics || [])
const dailyTrend = computed(() => resultJson.value.daily_trend || [])
const prediction = computed(() => resultJson.value.prediction || null)
const highRiskGrids = computed(() => resultJson.value.high_risk_grids || [])
const commonExposureAnalysis = computed(() => resultJson.value.common_exposure_analysis || [])

const districtPredictions = computed(() => prediction.value?.district_predictions || [])
const topCommonExposure = computed(() => commonExposureAnalysis.value.slice(0, 6))

const diseaseName = computed(() => resultJson.value.disease_name || '流感')

const analysisPeriodText = computed(() => {
  const period = resultJson.value.analysis_period || {}
  const start = period.start_date || '2026-04-01'
  const end = period.end_date || '2026-04-30'
  return `分析周期：${start} 至 ${end}`
})

const trendLevelText = computed(() => {
  const level = prediction.value?.trend_level
  if (level === 'rising') return '近期上升'
  if (level === 'falling') return '近期下降'
  return '趋势平稳'
})

const animationParties = computed(() => [
  { name: '长安区', role: '数据分析' },
  { name: '桥西区', role: '数据分析' },
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

function getRiskLevelText(level: string) {
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  }
  return map[level] || level || '-'
}

function getPlaceTypeText(type: string) {
  const map: Record<string, string> = {
    commercial: '商圈',
    hospital: '医院',
    market: '市场',
    transport: '交通枢纽',
    residential: '社区',
    office: '办公区',
  }
  return map[type] || type || '-'
}

function ensureChart(chartRef: typeof trendChart, domRef: typeof trendChartRef) {
  if (!domRef.value) return null
  if (!chartRef.value) {
    chartRef.value = echarts.init(domRef.value)
  }
  return chartRef.value
}

function renderTrendChart() {
  if (!dailyTrend.value.length) return
  const chart = ensureChart(trendChart, trendChartRef)
  if (!chart) return

  const dates = dailyTrend.value.map((item: any) => item.date?.slice(5) || item.date)
  const caseCounts = dailyTrend.value.map((item: any) => item.case_count || 0)
  const positiveCounts = dailyTrend.value.map((item: any) => item.positive_count || 0)
  const positiveRates = dailyTrend.value.map((item: any) => Number(((item.positive_rate || 0) * 100).toFixed(2)))

  chart.setOption({
    color: ['#409EFF', '#F56C6C', '#E6A23C'],
    tooltip: {
      trigger: 'axis',
      formatter(params: any[]) {
        const rows = params.map((p) => `${p.marker}${p.seriesName}：${p.seriesName.includes('率') ? p.value + '%' : p.value}`)
        return `${params[0]?.axisValue || ''}<br/>${rows.join('<br/>')}`
      },
    },
    legend: { top: 0, data: ['病例数', '阳性数', '阳性率'] },
    grid: { left: 42, right: 46, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '人数' },
      { type: 'value', name: '阳性率', axisLabel: { formatter: '{value}%' } },
    ],
    series: [
      {
        name: '病例数',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ])
        },
        data: caseCounts,
      },
      {
        name: '阳性数',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: positiveCounts,
      },
      {
        name: '阳性率',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        symbolSize: 6,
        lineStyle: { type: 'dashed' },
        data: positiveRates,
      },
    ],
  })
}

function renderDistrictChart() {
  if (!districtStatistics.value.length) return
  const chart = ensureChart(districtChart, districtChartRef)
  if (!chart) return

  const names = districtStatistics.value.map((item: any) => shortDistrictName(item.district_name))
  const caseCounts = districtStatistics.value.map((item: any) => item.case_count || 0)
  const positiveCounts = districtStatistics.value.map((item: any) => item.positive_count || 0)
  const recentCounts = districtStatistics.value.map((item: any) => item.recent_case_count || 0)

  chart.setOption({
    color: ['#409EFF', '#F56C6C', '#8E9EAB'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, data: ['病例数', '阳性数', '近期病例'] },
    grid: { left: 42, right: 20, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', name: '人数' },
    series: [
      { name: '病例数', type: 'bar', barMaxWidth: 32, data: caseCounts },
      { name: '阳性数', type: 'bar', barMaxWidth: 32, data: positiveCounts },
      { name: '近期病例', type: 'bar', barMaxWidth: 32, data: recentCounts },
    ],
  })
}

function renderRiskMapChart() {
  if (!highRiskGrids.value.length) return
  const chart = ensureChart(riskMapChart, riskMapChartRef)
  if (!chart) return

  const points = highRiskGrids.value
    .filter((item: any) => item.center_lon && item.center_lat)
    .map((item: any) => ({
      name: item.grid_name,
      value: [item.center_lon, item.center_lat, item.risk_score || 0, item.case_count_7d || 0, item.positive_count_7d || 0],
      item,
    }))

  if (!points.length) return

  const lons = points.map((p: any) => p.value[0])
  const lats = points.map((p: any) => p.value[1])
  const lonMin = Math.min(...lons) - 0.015
  const lonMax = Math.max(...lons) + 0.015
  const latMin = Math.min(...lats) - 0.01
  const latMax = Math.max(...lats) + 0.01

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter(params: any) {
        const item = params.data.item
        return [
          `<strong>${item.grid_name}</strong>`,
          `区县：${item.district_name || '-'}`,
          `场所：${getPlaceTypeText(item.place_type)}`,
          `近7日病例：${item.case_count_7d || 0}`,
          `近7日阳性：${item.positive_count_7d || 0}`,
          `阳性率：${formatRate(item.positive_rate_7d)}`,
          `风险分数：${item.risk_score?.toFixed?.(2) || item.risk_score || '-'}`,
        ].join('<br/>')
      },
    },
    grid: { left: 50, right: 24, top: 28, bottom: 42 },
    xAxis: {
      type: 'value',
      name: '经度',
      min: lonMin,
      max: lonMax,
      scale: true,
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    yAxis: {
      type: 'value',
      name: '纬度',
      min: latMin,
      max: latMax,
      scale: true,
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    visualMap: {
      min: 0,
      max: 100,
      dimension: 2,
      right: 10,
      bottom: 10,
      text: ['高风险', '低风险'],
      calculable: true,
      inRange: { color: ['#FFD666', '#FF7A45', '#CF1322'] },
    },
    series: [
      {
        name: '风险网格',
        type: 'scatter',
        data: points,
        symbolSize(value: number[]) {
          const riskScore = value[2] || 0
          const caseCount = value[3] || 0
          return Math.max(12, Math.min(42, riskScore / 3 + caseCount / 3))
        },
        emphasis: {
          focus: 'self',
          label: {
            show: true,
            formatter: '{b}',
            position: 'top',
          },
        },
      },
    ],
  })
}

function renderRiskRankChart() {
  if (!highRiskGrids.value.length) return
  const chart = ensureChart(riskRankChart, riskRankChartRef)
  if (!chart) return

  const topList = [...highRiskGrids.value]
    .sort((a: any, b: any) => (b.risk_score || 0) - (a.risk_score || 0))
    .slice(0, 10)
    .reverse()

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any[]) {
        const p = params[0]
        const item = p.data.raw
        return [
          `<strong>${item.grid_name}</strong>`,
          `风险分数：${item.risk_score?.toFixed?.(2) || item.risk_score || '-'}`,
          `近7日病例：${item.case_count_7d || 0}`,
          `近7日阳性：${item.positive_count_7d || 0}`,
        ].join('<br/>')
      },
    },
    grid: { left: 110, right: 24, top: 18, bottom: 28 },
    xAxis: { type: 'value', max: 100, name: '风险分数' },
    yAxis: {
      type: 'category',
      data: topList.map((item: any) => item.grid_name.replace(/^.*?-/, '')),
      axisLabel: { width: 92, overflow: 'truncate' },
    },
    series: [
      {
        name: '风险分数',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          // 使用回调函数动态分配颜色
          color: function(params: any) {
            const val = params.value || 0;
            if (val >= 90) {
              // 高分区间 (>=90)：深红渐变
              return new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                { offset: 0, color: '#CF1322' },
                { offset: 1, color: '#F56C6C' }
              ]);
            } else if (val >= 70) {
              // 中高分区间 (70~89)：橙红渐变
              return new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                { offset: 0, color: '#FF7A45' },
                { offset: 1, color: '#FFB08F' }
              ]);
            } else {
              // 较低分区间 (<70)：橙黄渐变
              return new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                { offset: 0, color: '#E6A23C' },
                { offset: 1, color: '#F3D19E' }
              ]);
            }
          }
        },
        data: topList.map((item: any) => ({ value: item.risk_score || 0, raw: item })),
        label: {
          show: true,
          position: 'right',
          formatter(params: any) {
            const value = Number(params.value || 0)
            return value.toFixed(0)
          },
        },
      },
    ],
  })
}

async function renderCharts() {
  await nextTick()
  if (running.value || !hasResult.value) return
  renderTrendChart()
  renderDistrictChart()
  renderRiskMapChart()
  renderRiskRankChart()
}

function resizeCharts() {
  trendChart.value?.resize()
  districtChart.value?.resize()
  riskMapChart.value?.resize()
  riskRankChart.value?.resize()
}

function disposeCharts() {
  trendChart.value?.dispose()
  districtChart.value?.dispose()
  riskMapChart.value?.dispose()
  riskRankChart.value?.dispose()
  trendChart.value = null
  districtChart.value = null
  riskMapChart.value = null
  riskRankChart.value = null
}

async function loadResult() {
  try {
    taskResult.value = unwrapResponse(await getTaskResult(taskId))
    await renderCharts()
  } catch (error) {
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
.t2-result-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at 12% 8%, rgba(64, 158, 255, 0.16), transparent 28%),
    radial-gradient(circle at 82% 12%, rgba(103, 194, 58, 0.14), transparent 30%),
    linear-gradient(135deg, #f5f8fc 0%, #edf2f7 100%);
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
  color: #17233d;
  font-size: 24px;
  font-weight: 700;
}

.title-area p {
  margin: 0;
  color: #6b778c;
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

.running-card {
  padding: 28px;
}

.result-header,
.overview-title,
.section-title,
.exposure-header,
.prediction-item {
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
  color: #24364f;
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
  color: #b7791f;
  background: #fff7e6;
}

.overview-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 24px;
}

.overview-main,
.prediction-card,
.chart-card,
.exposure-section {
  padding: 24px;
}

.overview-title {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.overview-title h2 {
  margin: 0 0 8px;
  color: #17233d;
  font-size: 22px;
  font-weight: 750;
}

.overview-title p,
.prediction-message,
.risk-reason,
.map-note {
  margin: 0;
  color: #6b778c;
  line-height: 1.7;
}

.trend-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88px;
  padding: 8px 14px;
  border-radius: 999px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  background: linear-gradient(135deg, #36cfc9, #409eff);
}

.trend-pill.rising {
  background: linear-gradient(135deg, #ff7a45, #f5222d);
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

.metric-card.danger {
  background: linear-gradient(180deg, #fff5f5, #ffffff);
  border-color: #ffe1e1;
}

.metric-card.warning {
  background: linear-gradient(180deg, #fff9ec, #ffffff);
  border-color: #faecd8;
}

.metric-card.purple {
  background: linear-gradient(180deg, #f7f3ff, #ffffff);
  border-color: #e6dcff;
}

.metric-card.danger-light {
  background: linear-gradient(180deg, #fff2f6, #ffffff);
  border-color: #ffd6e7;
}

.metric-label {
  display: block;
  margin-bottom: 10px;
  color: #7a869a;
  font-size: 13px;
}

.metric-card strong {
  color: #17233d;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 30px;
  line-height: 1;
}

.prediction-card {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.prediction-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.prediction-item {
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f7f9fc;
}

.prediction-item span,
.exposure-header h3 {
  color: #24364f;
  font-weight: 700;
}

.prediction-item small {
  display: block;
  margin-top: 4px;
  color: #8b97a8;
}

.prediction-item strong {
  color: #f56c6c;
  font-size: 22px;
}

.chart-grid {
  display: grid;
  gap: 24px;
}

.two-columns {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.map-layout {
  grid-template-columns: minmax(0, 1.3fr) minmax(360px, 0.7fr);
}

.chart-box {
  height: 360px;
}

.map-chart-box {
  height: 470px;
}

.rank-chart-box {
  height: 470px;
}

.map-note {
  margin-top: 8px;
  font-size: 12px;
}

.exposure-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.exposure-card {
  padding: 18px;
  border: 1px solid #edf1f7;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff, #ffffff);
}

.exposure-header {
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.exposure-header h3 {
  margin: 0;
  font-size: 16px;
}

.exposure-type {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  color: #409eff;
  background: #ecf5ff;
  font-size: 12px;
  font-weight: 700;
}

.exposure-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.exposure-metrics div {
  padding: 10px;
  border-radius: 12px;
  background: #f7f9fc;
}

.exposure-metrics span {
  display: block;
  margin-bottom: 6px;
  color: #8b97a8;
  font-size: 12px;
}

.exposure-metrics strong {
  color: #17233d;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 20px;
}

.risk-reason {
  min-height: 44px;
  font-size: 13px;
}

.district-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

@media (max-width: 1400px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .overview-section,
  .map-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1080px) {
  .two-columns,
  .exposure-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .t2-result-page {
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
  .exposure-metrics {
    grid-template-columns: 1fr 1fr;
  }
}
</style>