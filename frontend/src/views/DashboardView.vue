<template>
  <div class="dashboard-page">
    <header class="topbar">
      <div class="title-area">
        <h1>首页总览</h1>
        <p>生物安全数据联合统计系统运行态概览</p>
      </div>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadAll">
        刷新态势
      </el-button>
    </header>

    <main class="dashboard-content">
      <h3 class="section-title">全网资源基座</h3>
      <el-row :gutter="16" class="mb-4">
        <el-col :xs="24" :sm="12" :md="6" v-for="item in resourceCards" :key="item.key">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">{{ item.label }}</span>
              <el-icon :size="20" :color="item.color"><component :is="item.icon" /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="item.value" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16" class="mb-4">
        <el-col :xs="24" :sm="12" :md="6" v-for="item in taskCards" :key="item.key">
          <el-card shadow="hover" class="stat-card dark-card">
            <div class="stat-header">
              <span class="stat-label">{{ item.label }}</span>
            </div>
            <div class="stat-value">
              <el-statistic :value="item.value" value-style="color: #fff;" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <h3 class="section-title">联合计算态势</h3>
      <el-row :gutter="16" class="mb-4">
        <el-col :span="16">
          <el-card shadow="never" class="chart-card">
            <div class="card-header">
              <span>近 7 天联合任务执行趋势</span>
            </div>
            <div ref="trendChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" class="chart-card">
            <div class="card-header">
              <span>参与机构数据贡献度</span>
            </div>
            <div ref="nodeChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <h3 class="section-title">核心业务与审计追踪</h3>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never" class="table-card">
            <template #header>
              <div class="card-header">
                <span>最近联合统计任务</span>
                <el-tag type="primary" effect="plain">Task Scheduler</el-tag>
              </div>
            </template>
            <el-table :data="recentTasks" border stripe height="300">
              <el-table-column prop="task_name" label="任务名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getTaskStatusType(row.status)" effect="dark" size="small">
                    {{ row.status.toUpperCase() }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="触发时间" width="160" />
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card shadow="never" class="table-card">
            <template #header>
              <div class="card-header">
                <span>最新区块链存证审计</span>
                <el-tag type="success" effect="plain">Blockchain Audit</el-tag>
              </div>
            </template>
            <el-table :data="recentChainRecords" border stripe height="300">
              <el-table-column prop="biz_type" label="业务动作" width="120" />
              <el-table-column prop="tx_hash" label="存证哈希 (Tx Hash)" min-width="220">
                <template #default="{ row }">
                  <div class="hash-wrapper" @click="copyHash(row.tx_hash)" title="点击复制 Hash">
                    <el-icon class="hash-icon"><Link /></el-icon>
                    <span class="hash-text">{{ formatHash(row.tx_hash) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="上链时间" width="160" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import * as echarts from 'echarts'
// 请确保已在全局或此处引入 Element Plus Icons
import { Refresh, Link, OfficeBuilding, Connection, DataLine, Files } from '@element-plus/icons-vue'

import {
  getDashboardSummaryApi,
  getRecentTasksApi,
  getRecentChainRecordsApi,
} from '@/api/dashboard'

// --- Types ---
interface SummaryData {
  agency_count: number
  node_count: number
  dataset_count: number
  stat_template_count: number
  task_count: number
  success_task_count: number
  result_count: number
  chain_record_count: number
}

interface TaskItem {
  id: number
  task_code: string
  task_name: string
  status: string
  created_at: string
}

interface ChainRecordItem {
  id: number
  biz_type: string
  biz_id: string
  chain_type: string
  tx_hash: string
  status: string
  created_at: string
}

// --- Store & Router ---
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)

// --- Data Refs ---
const summary = ref<SummaryData>({
  agency_count: 0, node_count: 0, dataset_count: 0, stat_template_count: 0,
  task_count: 0, success_task_count: 0, result_count: 0, chain_record_count: 0
})
const recentTasks = ref<TaskItem[]>([])
const recentChainRecords = ref<ChainRecordItem[]>([])

// --- Chart Refs ---
const trendChartRef = ref<HTMLElement | null>(null)
const nodeChartRef = ref<HTMLElement | null>(null)
let trendChartInstance: echarts.ECharts | null = null
let nodeChartInstance: echarts.ECharts | null = null

// --- Computed ---
const resourceCards = computed(() => [
  { key: 'agency', label: '协作机构数', value: summary.value.agency_count, icon: OfficeBuilding, color: '#409EFF' },
  { key: 'node', label: '联邦节点数', value: summary.value.node_count, icon: Connection, color: '#67C23A' },
  { key: 'dataset', label: '数据资产量', value: summary.value.dataset_count, icon: DataLine, color: '#E6A23C' },
  { key: 'template', label: '可用算法模版', value: summary.value.stat_template_count, icon: Files, color: '#F56C6C' },
])

const taskCards = computed(() => [
  { key: 'tasks', label: '累计下发任务', value: summary.value.task_count },
  { key: 'success', label: '成功计算次数', value: summary.value.success_task_count },
  { key: 'results', label: '产出统计报告', value: summary.value.result_count },
  { key: 'chains', label: '区块链确权数', value: summary.value.chain_record_count },
])

// --- Methods ---
function getTaskStatusType(status: string) {
  const map: Record<string, string> = { success: 'success', running: 'warning', failed: 'danger' }
  return map[status] || 'info'
}

// 格式化 Hash，省略中间字符
function formatHash(hash: string) {
  if (!hash || hash.length < 16) return hash
  return `${hash.slice(0, 8)}......${hash.slice(-8)}`
}

// 复制 Hash 到剪贴板
async function copyHash(hash: string) {
  try {
    await navigator.clipboard.writeText(hash)
    ElMessage.success('区块链存证 Hash 已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

// --- ECharts 初始化 ---
function initCharts() {
  if (trendChartRef.value) {
    trendChartInstance = echarts.init(trendChartRef.value)
    trendChartInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
      yAxis: { type: 'value' },
      series: [
        {
          name: '任务执行量',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.1, color: '#409EFF' },
          itemStyle: { color: '#409EFF' },
          data: [12, 19, 15, 26, 22, 34, 40] // 演示数据，可替换为真实 API 数据
        }
      ]
    })
  }

  if (nodeChartRef.value) {
    nodeChartInstance = echarts.init(nodeChartRef.value)
    nodeChartInstance.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: '0%', left: 'center' },
      series: [
        {
          name: '数据贡献度',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: [
            { value: 1048, name: '市中心医院' },
            { value: 735, name: '第一人民医院' },
            { value: 580, name: '妇幼保健院' },
            { value: 300, name: '社区服务中心' }
          ] // 演示数据
        }
      ]
    })
  }
}

// --- API Calls ---
async function loadAll() {
  loading.value = true
  try {
    const [sumRes, taskRes, chainRes] = await Promise.all([
      getDashboardSummaryApi(),
      getRecentTasksApi(10), // 加载 10 条填满表格
      getRecentChainRecordsApi(10)
    ])
    summary.value = (sumRes as any).data || summary.value
    recentTasks.value = (taskRes as any).data || []
    recentChainRecords.value = (chainRes as any).data || []
  } catch (error) {
    console.error(error)
    ElMessage.error('首页数据加载失败')
  } finally {
    loading.value = false
  }
}

// --- Lifecycle ---
onMounted(async () => {
  await loadAll()
  nextTick(() => {
    initCharts()
    // 监听窗口大小变化自适应图表
    window.addEventListener('resize', () => {
      trendChartInstance?.resize()
      nodeChartInstance?.resize()
    })
  })
})

onBeforeUnmount(() => {
  trendChartInstance?.dispose()
  nodeChartInstance?.dispose()
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: #f0f2f5;
}

.topbar {
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

.dashboard-content {
  padding: 24px;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #374151;
  font-weight: 600;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.mb-4 {
  margin-bottom: 24px;
}

/* 统计卡片样式 */
.stat-card {
  border-radius: 8px;
  border: none;
}
.dark-card {
  background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
  color: #ffffff;
}
.dark-card .stat-label {
  color: #9ca3af;
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-label {
  color: #6b7280;
  font-size: 14px;
}
.stat-value {
  margin-top: 16px;
}

/* 图表容器 */
.chart-card {
  border-radius: 8px;
}
.chart-container {
  height: 280px;
  width: 100%;
}

/* 表格头部 */
.table-card {
  border-radius: 8px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

/* Hash 极客样式 */
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
</style>