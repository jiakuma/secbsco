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
          <div class="chain-toolbar">
            <el-select
              v-model="chainQuery.biz_type"
              placeholder="业务类型"
              clearable
              style="width: 160px"
            >
              <el-option label="任务存证" value="task" />
              <el-option label="结果存证" value="task_result" />
              <el-option label="审计存证" value="audit_log" />
            </el-select>

            <el-select
              v-model="chainQuery.status"
              placeholder="存证状态"
              clearable
              style="width: 140px"
            >
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
            </el-select>

            <el-button type="primary" @click="handleSearchChainRecords">
              查询
            </el-button>

            <el-button @click="handleResetChainRecords">
              重置
            </el-button>
          </div>

          <el-table :data="chainRecords" border stripe>
            <el-table-column prop="id" label="存证ID" width="90" />

            <el-table-column label="业务类型" width="140">
              <template #default="{ row }">
                <el-tag type="primary">
                  {{ formatBizType(row.biz_type) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="biz_id" label="业务ID" width="120" />

            <el-table-column prop="content_hash" label="内容哈希" min-width="260" show-overflow-tooltip />

            <el-table-column prop="chain_type" label="链类型" width="150" />

            <el-table-column prop="tx_hash" label="交易哈希" min-width="280" show-overflow-tooltip />

            <el-table-column prop="block_number" label="区块高度" width="140" />

            <el-table-column prop="contract_address" label="合约地址" min-width="180" show-overflow-tooltip />

            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'info'">
                  {{ row.status || '-' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :total="chainTotal"
              :page-size="chainQuery.page_size"
              :current-page="chainQuery.page"
              @current-change="handleChainPageChange"
            />
          </div>
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
} from '@/api/dashboard'

import { getChainRecordList } from '@/api/chainRecord'

const loading = ref(false)
const activeTab = ref('audit')

const summary = ref<any>({})
const auditLogs = ref<any[]>([])
const chainRecords = ref<any[]>([])
const chainQuery = ref({
  page: 1,
  page_size: 10,
  biz_type: '',
  status: '',
})

const chainTotal = ref(0)
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
  const params: any = {
    page: chainQuery.value.page,
    page_size: chainQuery.value.page_size,
  }

  if (chainQuery.value.biz_type) {
    params.biz_type = chainQuery.value.biz_type
  }

  if (chainQuery.value.status) {
    params.status = chainQuery.value.status
  }

  const res = await getChainRecordList(params)
  const data = unwrapResponse(res) || {}

  chainRecords.value = data.items || []
  chainTotal.value = data.total || 0
}

function handleSearchChainRecords() {
  chainQuery.value.page = 1
  loadChainRecords()
}

function handleResetChainRecords() {
  chainQuery.value = {
    page: 1,
    page_size: 10,
    biz_type: '',
    status: '',
  }

  loadChainRecords()
}

function handleChainPageChange(page: number) {
  chainQuery.value.page = page
  loadChainRecords()
}

function formatBizType(type: string) {
  const map: Record<string, string> = {
    task: '任务存证',
    task_result: '结果存证',
    audit_log: '审计存证',
  }

  return map[type] || type || '-'
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

.chain-toolbar {
  margin-bottom: 14px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.main-card {
  border-radius: 14px;
}
</style>