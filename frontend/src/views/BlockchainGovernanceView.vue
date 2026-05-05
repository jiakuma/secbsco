<template>
  <div class="blockchain-page">
    <div class="page-header">
      <div>
        <h2>区块链治理</h2>
        <p>查看任务审计、结果存证与链上交易记录</p>
      </div>

      <el-button type="primary" :loading="loading" @click="loadAll">
        刷新
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">审计日志数</div>
          <div class="stat-value">{{ summary.audit_log_count || 0 }}</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">存证记录数</div>
          <div class="stat-value">{{ summary.chain_record_count || 0 }}</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">任务总数</div>
          <div class="stat-value">{{ summary.task_count || 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="最近审计" name="audit">
          <el-table :data="auditLogs" border stripe>
            <el-table-column prop="id" label="日志ID" width="90" />
            <el-table-column prop="operation_type" label="操作类型" min-width="160" />
            <el-table-column prop="object_type" label="对象类型" width="130" />
            <el-table-column prop="object_id" label="对象ID" width="120" />
            <el-table-column prop="operation_desc" label="操作说明" min-width="240" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="链上存证" name="chain">
          <el-table :data="chainRecords" border stripe>
            <el-table-column prop="id" label="存证ID" width="90" />
            <el-table-column prop="biz_type" label="业务类型" width="140" />
            <el-table-column prop="biz_id" label="业务ID" width="120" />
            <el-table-column prop="chain_type" label="链类型" width="140" />
            <el-table-column prop="tx_hash" label="交易哈希" min-width="280" show-overflow-tooltip />
            <el-table-column prop="block_number" label="区块高度" width="140" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'info'">
                  {{ row.status || '-' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDashboardSummaryApi,
  getRecentAuditLogsApi,
  getRecentChainRecordsApi,
} from '@/api/dashboard'

const loading = ref(false)
const activeTab = ref('audit')

const summary = ref<any>({})
const auditLogs = ref<any[]>([])
const chainRecords = ref<any[]>([])

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

async function loadSummary() {
  const res = await getDashboardSummaryApi()
  summary.value = unwrapResponse(res) || {}
}

async function loadAuditLogs() {
  const res = await getRecentAuditLogsApi(20)
  auditLogs.value = unwrapResponse(res) || []
}

async function loadChainRecords() {
  const res = await getRecentChainRecordsApi(20)
  chainRecords.value = unwrapResponse(res) || []
}

async function loadAll() {
  loading.value = true

  try {
    await Promise.all([
      loadSummary(),
      loadAuditLogs(),
      loadChainRecords(),
    ])
  } catch (error) {
    console.error(error)
    ElMessage.error('区块链治理数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.blockchain-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  color: #1f2937;
}

.page-header p {
  margin: 6px 0 0;
  color: #8a96a8;
  font-size: 13px;
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

.main-card {
  border-radius: 14px;
}
</style>