<template>
  <div class="dashboard-page">
    <header class="topbar">
      <div>
        <h1>首页总览</h1>
        <p>生物安全数据联合统计系统运行态概览</p>
      </div>

      <el-button type="primary" :loading="loading" @click="loadAll">
        刷新数据
      </el-button>
    </header>

    <main class="dashboard-content">
      <!-- 统计卡片 -->
      <el-row :gutter="16">
        <el-col
          v-for="item in cards"
          :key="item.key"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-card shadow="hover" class="stat-card">
            <div class="stat-label">{{ item.label }}</div>
            <div class="stat-value">{{ item.value }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 接口联调状态 -->
      <el-card shadow="never" class="info-card">
        <template #header>
          <div class="card-header">
            <span>接口联调状态</span>
            <el-button type="primary" size="small" :loading="loading" @click="loadAll">
              刷新
            </el-button>
          </div>
        </template>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="后端地址">
            {{ apiBaseUrl }}
          </el-descriptions-item>
          <el-descriptions-item label="登录状态">
            已登录
          </el-descriptions-item>
          <el-descriptions-item label="Dashboard 接口">
            summary / recent-tasks / recent-results / recent-audit-logs / recent-chain-records
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 最近任务 -->
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>最近联合统计任务</span>
            <el-tag type="primary">recent-tasks</el-tag>
          </div>
        </template>

        <el-table :data="recentTasks" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="task_code" label="任务编码" min-width="180" />
          <el-table-column prop="task_name" label="任务名称" min-width="220" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getTaskStatusType(row.status)">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </el-card>

      <!-- 最近结果 -->
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>最近统计结果</span>
            <el-tag type="success">recent-results</el-tag>
          </div>
        </template>

        <el-table :data="recentResults" border stripe>
          <el-table-column prop="id" label="结果ID" width="90" />
          <el-table-column prop="task_id" label="任务ID" width="90" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'info'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result_hash" label="结果哈希" min-width="260" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </el-card>

      <!-- 最近审计日志 -->
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>最近审计日志</span>
            <el-tag type="warning">recent-audit-logs</el-tag>
          </div>
        </template>

        <el-table :data="recentAuditLogs" border stripe>
          <el-table-column prop="id" label="日志ID" width="90" />
          <el-table-column prop="operation_type" label="操作类型" min-width="160" />
          <el-table-column prop="object_type" label="对象类型" width="120" />
          <el-table-column prop="object_id" label="对象ID" width="120" />
          <el-table-column prop="operation_desc" label="操作说明" min-width="220" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </el-card>

      <!-- 最近链上存证 -->
      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>最近链上存证记录</span>
            <el-tag type="danger">recent-chain-records</el-tag>
          </div>
        </template>

        <el-table :data="recentChainRecords" border stripe>
          <el-table-column prop="id" label="存证ID" width="90" />
          <el-table-column prop="biz_type" label="业务类型" width="140" />
          <el-table-column prop="biz_id" label="业务ID" width="120" />
          <el-table-column prop="chain_type" label="链类型" width="140" />
          <el-table-column prop="tx_hash" label="交易哈希" min-width="260" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'info'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </el-card>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  getDashboardSummaryApi,
  getRecentTasksApi,
  getRecentResultsApi,
  getRecentAuditLogsApi,
  getRecentChainRecordsApi,
} from '@/api/dashboard'

const router = useRouter()
const authStore = useAuthStore()

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const loading = ref(false)

const summary = ref<any>({
  agency_count: 0,
  node_count: 0,
  dataset_count: 0,
  stat_template_count: 0,
  task_count: 0,
  success_task_count: 0,
  result_count: 0,
  audit_log_count: 0,
  chain_record_count: 0,
})

const recentTasks = ref<any[]>([])
const recentResults = ref<any[]>([])
const recentAuditLogs = ref<any[]>([])
const recentChainRecords = ref<any[]>([])

const username = computed(() => {
  return authStore.userInfo?.username || authStore.userInfo?.real_name || '当前用户'
})

const cards = computed(() => [
  {
    key: 'agency_count',
    label: '机构数量',
    value: summary.value.agency_count,
  },
  {
    key: 'node_count',
    label: '节点数量',
    value: summary.value.node_count,
  },
  {
    key: 'dataset_count',
    label: '数据集数量',
    value: summary.value.dataset_count,
  },
  {
    key: 'stat_template_count',
    label: '统计模板数量',
    value: summary.value.stat_template_count,
  },
  {
    key: 'task_count',
    label: '任务总数',
    value: summary.value.task_count,
  },
  {
    key: 'success_task_count',
    label: '成功任务数',
    value: summary.value.success_task_count,
  },
  {
    key: 'result_count',
    label: '统计结果数',
    value: summary.value.result_count,
  },
  {
    key: 'audit_log_count',
    label: '审计日志数',
    value: summary.value.audit_log_count,
  },
  {
    key: 'chain_record_count',
    label: '存证记录数',
    value: summary.value.chain_record_count,
  },
])

function getTaskStatusType(status: string) {
  if (status === 'success') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

async function loadSummary() {
  const res: any = await getDashboardSummaryApi()
  summary.value = res.data || {}
}

async function loadRecentTasks() {
  const res: any = await getRecentTasksApi(5)
  recentTasks.value = res.data || []
}

async function loadRecentResults() {
  const res: any = await getRecentResultsApi(5)
  recentResults.value = res.data || []
}

async function loadRecentAuditLogs() {
  const res: any = await getRecentAuditLogsApi(5)
  recentAuditLogs.value = res.data || []
}

async function loadRecentChainRecords() {
  const res: any = await getRecentChainRecordsApi(5)
  recentChainRecords.value = res.data || []
}

async function loadAll() {
  loading.value = true

  try {
    await Promise.all([
      loadSummary(),
      loadRecentTasks(),
      loadRecentResults(),
      loadRecentAuditLogs(),
      loadRecentChainRecords(),
    ])
  } catch (error) {
    console.error(error)
    ElMessage.error('首页数据加载失败')
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(async () => {
  try {
    if (!authStore.userInfo) {
      await authStore.fetchMe()
    }

    await loadAll()
  } catch (error) {
    console.error(error)
  }
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.topbar {
  height: 76px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.topbar h1 {
  margin: 0;
  font-size: 22px;
  color: #1f2937;
}

.topbar p {
  margin: 6px 0 0;
  color: #8a96a8;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info {
  color: #4b5563;
  font-size: 14px;
}

.dashboard-content {
  padding: 24px;
}

.stat-card {
  margin-bottom: 16px;
  border-radius: 14px;
}

.stat-label {
  color: #8a96a8;
  font-size: 14px;
}

.stat-value {
  margin-top: 10px;
  color: #1f2937;
  font-size: 30px;
  font-weight: 700;
}

.info-card {
  margin-top: 12px;
  border-radius: 14px;
}

.table-card {
  margin-top: 18px;
  border-radius: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>