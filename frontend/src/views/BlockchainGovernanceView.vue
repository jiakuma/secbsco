<template>
  <div class="blockchain-page">
    <div class="page-header">
      <div>
        <h2>区块链治理</h2>
        <p>统一查看审计日志、存证摘要与链上凭证</p>
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

            <el-input
              v-model="chainQuery.biz_id"
              placeholder="业务ID"
              clearable
              style="width: 160px"
            />

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

            <el-table-column label="存证摘要" min-width="260">
              <template #default="{ row }">
                <div class="hash-brief">
                  {{ shortHash(row.content_hash) }}
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="chain_type" label="链类型" width="150" />

            <el-table-column label="链上凭证" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.tx_hash" type="success" effect="plain">已生成</el-tag>
                <el-tag v-else type="info" effect="plain">未生成</el-tag>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)">
                  {{ formatStatus(row.status) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="创建时间" min-width="180" />

            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  :loading="detailLoading && currentChainRecord?.id === row.id"
                  @click="handleViewChainRecordDetail(row)"
                >
                  查看凭证
                </el-button>

                <el-button
                  v-if="getRelatedTask(row)?.task_id"
                  type="success"
                  link
                  @click="goTaskDetail(getRelatedTask(row)?.task_id)"
                >
                  任务详情
                </el-button>


                <el-button
                  type="warning"
                  link
                  :loading="auditLinkLoading && currentAuditChainRecord?.id === row.id"
                  @click="handleViewRelatedAuditLogs(row)"
                >
                  关联审计
                </el-button>
              </template>
            </el-table-column>
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

    <el-dialog
      v-model="chainDetailVisible"
      title="链上存证凭证"
      width="860px"
      destroy-on-close
    >
      <div v-if="currentChainRecord" class="detail-content">
        <div class="credential-summary">
          <div class="summary-item">
            <div class="summary-label">存证对象</div>
            <div class="summary-value">
              {{ formatBizType(currentChainRecord.biz_type) }} #{{ currentChainRecord.biz_id || '-' }}
            </div>
          </div>

          <div class="summary-item">
            <div class="summary-label">关联任务</div>
            <div class="summary-value">
              <template v-if="getRelatedTask(currentChainRecord)">
                任务 #{{ getRelatedTask(currentChainRecord)?.task_id }}
              </template>
              <template v-else>未关联</template>
            </div>
          </div>

          <div class="summary-item">
            <div class="summary-label">存证状态</div>
            <div class="summary-value">
              <el-tag :type="getStatusTagType(currentChainRecord.status)">
                {{ formatStatus(currentChainRecord.status) }}
              </el-tag>
            </div>
          </div>
        </div>

        <el-alert
          class="detail-alert"
          :title="getCredentialTip(currentChainRecord)"
          type="info"
          show-icon
          :closable="false"
        />

        <div class="detail-section-title">业务对象</div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="存证ID">
            {{ currentChainRecord.id }}
          </el-descriptions-item>

          <el-descriptions-item label="业务类型">
            {{ formatBizType(currentChainRecord.biz_type) }}
          </el-descriptions-item>

          <el-descriptions-item label="业务ID">
            {{ currentChainRecord.biz_id || '-' }}
          </el-descriptions-item>

          <el-descriptions-item label="创建时间">
            {{ currentChainRecord.created_at || '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="getRelatedTask(currentChainRecord)">
          <div class="detail-section-title">关联任务</div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="任务ID">
              {{ getRelatedTask(currentChainRecord)?.task_id }}
            </el-descriptions-item>

            <el-descriptions-item label="任务状态">
              {{ getRelatedTask(currentChainRecord)?.task_status || '-' }}
            </el-descriptions-item>

            <el-descriptions-item label="任务编号">
              {{ getRelatedTask(currentChainRecord)?.task_code || '-' }}
            </el-descriptions-item>

            <el-descriptions-item label="任务名称">
              {{ getRelatedTask(currentChainRecord)?.task_name || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="detail-actions">
            <el-button type="primary" plain @click="goTaskDetail(getRelatedTask(currentChainRecord)?.task_id)">
              跳转任务详情
            </el-button>

            <el-button
              type="warning"
              plain
              :loading="auditLinkLoading && currentAuditChainRecord?.id === currentChainRecord.id"
              @click="handleViewRelatedAuditLogs(currentChainRecord)"
            >
              查看关联审计
            </el-button>
          </div>
        </template>

        <div class="detail-section-title">链上凭证</div>

        <div class="credential-grid">
          <div class="credential-row">
            <div class="credential-label">内容哈希</div>
            <div class="credential-value">{{ currentChainRecord.content_hash || '-' }}</div>
            <el-button link type="primary" @click="copyText(currentChainRecord.content_hash)">
              复制
            </el-button>
          </div>

          <div class="credential-row">
            <div class="credential-label">交易哈希</div>
            <div class="credential-value">{{ currentChainRecord.tx_hash || '-' }}</div>
            <el-button link type="primary" @click="copyText(currentChainRecord.tx_hash)">
              复制
            </el-button>
          </div>

          <div class="credential-row">
            <div class="credential-label">区块高度</div>
            <div class="credential-value">{{ currentChainRecord.block_number ?? '-' }}</div>
            <el-button link type="primary" @click="copyText(currentChainRecord.block_number)">
              复制
            </el-button>
          </div>

          <div class="credential-row">
            <div class="credential-label">合约地址</div>
            <div class="credential-value">{{ currentChainRecord.contract_address || '-' }}</div>
            <el-button link type="primary" @click="copyText(currentChainRecord.contract_address)">
              复制
            </el-button>
          </div>
        </div>

        <div class="detail-section-title">校验说明</div>

        <div class="verify-box">
          <div class="verify-item">
            <span class="verify-dot" />
            <span>内容哈希用于证明业务结果摘要未被篡改。</span>
          </div>
          <div class="verify-item">
            <span class="verify-dot" />
            <span>交易哈希、区块高度和合约地址共同构成链上查询凭证。</span>
          </div>
          <div class="verify-item">
            <span class="verify-dot" />
            <span>当前阶段为 Mock 存证，第十八阶段接入 FISCO BCOS 后替换为真实链返回值。</span>
          </div>
        </div>

        <template v-if="currentChainRecord.error_message">
          <div class="detail-section-title">错误信息</div>

          <el-alert
            :title="currentChainRecord.error_message"
            type="error"
            show-icon
            :closable="false"
          />
        </template>
      </div>

      <template #footer>
        <el-button @click="chainDetailVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="auditDetailVisible"
      title="关联审计日志"
      width="960px"
      destroy-on-close
    >
      <div class="audit-link-dialog">
        <div v-if="currentAuditChainRecord" class="audit-link-summary">
          <div>
            <span class="audit-link-label">存证记录：</span>
            <span>#{{ currentAuditChainRecord.id }}</span>
          </div>
          <div>
            <span class="audit-link-label">业务对象：</span>
            <span>{{ formatBizType(currentAuditChainRecord.biz_type) }} #{{ currentAuditChainRecord.biz_id || '-' }}</span>
          </div>
          <div v-if="getRelatedTask(currentAuditChainRecord)">
            <span class="audit-link-label">关联任务：</span>
            <el-button type="primary" link @click="goTaskDetail(getRelatedTask(currentAuditChainRecord)?.task_id)">
              任务 #{{ getRelatedTask(currentAuditChainRecord)?.task_id }}
            </el-button>
          </div>
        </div>

        <el-alert
          class="detail-alert"
          title="优先按 object_type=chain_record、object_id=存证ID 精确查询；如无记录，则按业务类型和关联任务进行补充查询。"
          type="info"
          show-icon
          :closable="false"
        />

        <el-table
          v-loading="auditLinkLoading"
          :data="relatedAuditLogs"
          border
          stripe
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="audit-expand">
                <div class="audit-json-card">
                  <div class="audit-json-title">请求参数</div>
                  <pre>{{ formatJson(row.request_json) }}</pre>
                </div>

                <div class="audit-json-card">
                  <div class="audit-json-title">操作结果</div>
                  <pre>{{ formatJson(row.result_json) }}</pre>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="id" label="日志ID" width="90" />
          <el-table-column label="操作类型" min-width="180">
            <template #default="{ row }">
              {{ formatOperationType(row.operation_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="object_type" label="对象类型" width="130" />
          <el-table-column prop="object_id" label="对象ID" width="110" />
          <el-table-column prop="operation_desc" label="操作说明" min-width="240" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>

        <el-empty
          v-if="!auditLinkLoading && relatedAuditLogs.length === 0"
          description="暂无关联审计日志"
        />
      </div>

      <template #footer>
        <el-button @click="auditDetailVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getDashboardSummaryApi,
  getRecentAuditLogsApi,
} from '@/api/dashboard'

import {
  getChainRecordList,
  getChainRecordDetail,
} from '@/api/chainRecord'

import {
  getAuditLogList,
  getAuditLogDetail,
} from '@/api/auditLog'

const router = useRouter()

const loading = ref(false)
const activeTab = ref('audit')

const summary = ref<any>({})
const auditLogs = ref<any[]>([])

const chainRecords = ref<any[]>([])
const chainTotal = ref(0)

const chainQuery = ref({
  page: 1,
  page_size: 10,
  biz_type: '',
  biz_id: '',
  status: '',
})

const detailLoading = ref(false)
const chainDetailVisible = ref(false)
const currentChainRecord = ref<any>(null)

const auditLinkLoading = ref(false)
const auditDetailVisible = ref(false)
const currentAuditChainRecord = ref<any>(null)
const relatedAuditLogs = ref<any[]>([])
const relatedAuditTotal = ref(0)

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

  if (chainQuery.value.biz_id) {
    params.biz_id = chainQuery.value.biz_id
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
    biz_id: '',
    status: '',
  }

  loadChainRecords()
}

function handleChainPageChange(page: number) {
  chainQuery.value.page = page
  loadChainRecords()
}

async function handleViewChainRecordDetail(row: any) {
  if (!row?.id) {
    ElMessage.warning('存证记录ID不存在')
    return
  }

  detailLoading.value = true
  currentChainRecord.value = row

  try {
    const res = await getChainRecordDetail(row.id)
    currentChainRecord.value = unwrapResponse(res) || row
    chainDetailVisible.value = true
  } catch (error) {
    console.error(error)
    ElMessage.error('存证详情加载失败')
  } finally {
    detailLoading.value = false
  }
}


async function queryAuditLogs(params: any) {
  const res = await getAuditLogList(params)
  const data = unwrapResponse(res) || {}

  return {
    total: data.total || 0,
    items: data.items || [],
  }
}

async function querySingleAuditLog(logId: number | string | null | undefined) {
  if (!logId) {
    return []
  }

  try {
    const res = await getAuditLogDetail(logId)
    const data = unwrapResponse(res)
    return data ? [data] : []
  } catch (error) {
    console.warn('审计日志详情补充查询失败', error)
    return []
  }
}

async function handleViewRelatedAuditLogs(row: any) {
  if (!row?.id) {
    ElMessage.warning('存证记录ID不存在')
    return
  }

  auditLinkLoading.value = true
  currentAuditChainRecord.value = row
  relatedAuditLogs.value = []
  relatedAuditTotal.value = 0

  try {
    const primary = await queryAuditLogs({
      page: 1,
      page_size: 20,
      object_type: 'chain_record',
      object_id: String(row.id),
    })

    let items = primary.items
    let total = primary.total

    if (items.length === 0 && row.biz_type === 'audit_log') {
      items = await querySingleAuditLog(row.biz_id)
      total = items.length
    }

    const relatedTask = getRelatedTask(row)

    if (items.length === 0 && relatedTask?.task_id) {
      const fallback = await queryAuditLogs({
        page: 1,
        page_size: 20,
        task_id: relatedTask.task_id,
        operation_type: 'TASK_RESULT_CHAIN_ANCHOR',
      })

      items = fallback.items
      total = fallback.total
    }

    relatedAuditLogs.value = items
    relatedAuditTotal.value = total
    auditDetailVisible.value = true
  } catch (error) {
    console.error(error)
    ElMessage.error('关联审计日志加载失败')
  } finally {
    auditLinkLoading.value = false
  }
}

function getRelatedTask(record: any) {
  return record?.related_task || null
}

function goTaskDetail(taskId: number | string | null | undefined) {
  if (!taskId) {
    ElMessage.warning('当前存证记录未关联任务')
    return
  }

  chainDetailVisible.value = false
  router.push(`/tasks/${taskId}`)
}

function formatBizType(type: string) {
  const map: Record<string, string> = {
    task: '任务存证',
    task_result: '结果存证',
    audit_log: '审计存证',
  }

  return map[type] || type || '-'
}

function formatStatus(status: string) {
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    pending: '待处理',
  }

  return map[status] || status || '-'
}

function getStatusTagType(status: string) {
  if (status === 'success') {
    return 'success'
  }

  if (status === 'failed') {
    return 'danger'
  }

  return 'info'
}

function shortHash(value: string | null | undefined) {
  if (!value) {
    return '-'
  }

  if (value.length <= 24) {
    return value
  }

  return `${value.slice(0, 12)}...${value.slice(-10)}`
}

function getCredentialTip(record: any) {
  const bizType = record?.biz_type

  if (bizType === 'task_result') {
    return '当前记录是任务结果存证，业务ID对应 task_result.id，用于证明任务结果摘要已完成可信留痕。'
  }

  if (bizType === 'task') {
    return '当前记录是任务存证，用于证明任务创建、配置或任务摘要已完成可信留痕。'
  }

  if (bizType === 'audit_log') {
    return '当前记录是审计存证，用于证明关键操作日志已完成可信留痕。'
  }

  return '当前记录用于展示业务对象与链上凭证之间的映射关系。'
}


function formatOperationType(type: string) {
  const map: Record<string, string> = {
    TASK_CREATE: '任务创建',
    TASK_RUN: '任务执行',
    TASK_RESULT_CHAIN_ANCHOR: '任务结果存证',
    TASK_PARTY_CREATE: '参与方创建',
    TASK_PARTY_UPDATE: '参与方更新',
    TASK_PARTY_DELETE: '参与方删除',
  }

  return map[type] || type || '-'
}

function formatJson(value: any) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

async function copyText(text: string | number | null | undefined) {
  const value = String(text ?? '')

  if (!value) {
    ElMessage.warning('暂无可复制内容')
    return
  }

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = value
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }

    ElMessage.success('已复制')
  } catch (error) {
    console.error(error)
    ElMessage.error('复制失败')
  }
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


.empty-text {
  color: #a8abb2;
}

.hash-brief {
  color: #1f2937;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.detail-content {
  padding: 4px 0;
}

.credential-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.summary-item {
  padding: 14px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafcff;
}

.summary-label {
  margin-bottom: 8px;
  color: #8a96a8;
  font-size: 12px;
}

.summary-value {
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
  word-break: break-all;
}

.detail-alert {
  margin-bottom: 16px;
}

.detail-section-title {
  margin: 18px 0 10px;
  color: #1f2937;
  font-size: 15px;
  font-weight: 600;
}

.detail-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.credential-grid {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.credential-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  font-size: 13px;
}

.credential-row:last-child {
  border-bottom: none;
}

.credential-label {
  width: 80px;
  flex-shrink: 0;
  color: #606266;
}

.credential-value {
  flex: 1;
  min-width: 0;
  color: #1f2937;
  word-break: break-all;
  font-family: Consolas, Monaco, monospace;
}

.verify-box {
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafafa;
}

.verify-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #606266;
  font-size: 13px;
  line-height: 1.8;
}

.verify-dot {
  width: 6px;
  height: 6px;
  margin-top: 9px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
}


.audit-link-summary {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fafcff;
  color: #1f2937;
  font-size: 13px;
}

.audit-link-label {
  color: #8a96a8;
}

.audit-expand {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 8px 12px 12px;
}

.audit-json-card {
  min-width: 0;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}

.audit-json-title {
  padding: 8px 10px;
  border-bottom: 1px solid #ebeef5;
  color: #606266;
  font-size: 13px;
  font-weight: 600;
  background: #f5f7fa;
}

.audit-json-card pre {
  max-height: 240px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  color: #1f2937;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

</style>
