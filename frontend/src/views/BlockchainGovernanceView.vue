<template>
  <div class="blockchain-page">
    <header class="page-header">
      <div class="title-area">
        <h1>区块链治理与审计大盘</h1>
        <p>统一查看系统审计日志、FISCO BCOS 存证记录与链上校验凭证</p>
      </div>

      <div class="header-actions">
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadAll">
          刷新全局视图
        </el-button>
      </div>
    </header>

    <main class="page-content">
      <el-row :gutter="16" class="mb-4">
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">系统审计日志数</span>
              <el-icon :size="20" color="#409EFF"><Monitor /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="summary.audit_log_count || 0" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">可信存证记录数</span>
              <el-icon :size="20" color="#67C23A"><Link /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="summary.chain_record_count || 0" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card dark-card">
            <div class="stat-header">
              <span class="stat-label">业务任务总数</span>
              <el-icon :size="20" color="#E6A23C"><DataBoard /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="summary.task_count || 0" value-style="color: #fff;" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <h3 class="section-title">审计与存证追踪矩阵</h3>
      <el-card shadow="never" class="table-card">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane label="最近系统审计" name="audit">
            <el-table :data="auditLogs" border stripe>
              <el-table-column prop="id" label="日志ID" width="90" align="center">
                <template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template>
              </el-table-column>
              <el-table-column prop="operation_type" label="操作指令 (Operation Type)" min-width="200" >
                <template #default="{ row }">
                  <el-tag type="info" effect="plain" class="mono-text">{{ row.operation_type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="object_type" label="对象类型" width="140" align="center" />
              <el-table-column prop="object_id" label="对象ID" width="120" align="center">
                <template #default="{ row }"><span class="mono-text text-blue">{{ row.object_id }}</span></template>
              </el-table-column>
              <el-table-column prop="operation_desc" label="操作说明" min-width="240" show-overflow-tooltip />
              <el-table-column prop="created_at" label="操作时间" width="180" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="链上存证记录" name="chain">
            <div class="chain-toolbar">
              <el-select v-model="chainQuery.biz_type" placeholder="业务类型" clearable style="width: 160px">
                <el-option label="任务存证" value="task" />
                <el-option label="任务结果存证" value="task_result" />
                <el-option label="审计日志存证" value="audit_log" />
              </el-select>
              <el-input v-model="chainQuery.biz_id" placeholder="业务ID" clearable style="width: 160px" class="mono-input" />
              <el-select v-model="chainQuery.status" placeholder="上链状态" clearable style="width: 140px">
                <el-option label="已上链" value="success" />
                <el-option label="上链失败" value="failed" />
              </el-select>
              <el-button type="primary" :icon="Search" @click="handleSearchChainRecords">检索存证记录</el-button>
              <el-button :icon="RefreshLeft" @click="handleResetChainRecords">重置</el-button>
            </div>

            <el-table :data="chainRecords" border stripe>
              <el-table-column prop="id" label="存证ID" width="90" align="center">
                <template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template>
              </el-table-column>

              <el-table-column label="业务类型" width="120" align="center">
                <template #default="{ row }">
                  <el-tag type="primary" effect="plain">{{ formatBizType(row.biz_type) }}</el-tag>
                </template>
              </el-table-column>

              <el-table-column label="存证摘要 (Content Hash)" min-width="240">
                <template #default="{ row }">
                  <div class="hash-wrapper w-full" title="点击复制" @click="copyText(row.content_hash)">
                    <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                    <span class="hash-text">{{ shortHash(row.content_hash) }}</span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column label="交易哈希" min-width="220">
                <template #default="{ row }">
                  <div class="hash-wrapper w-full" :class="{ 'muted-hash': !row.tx_hash }" title="点击复制" @click="copyText(row.tx_hash)">
                    <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                    <span class="hash-text">{{ shortHash(row.tx_hash) }}</span>
                  </div>
                </template>
              </el-table-column>

              <el-table-column label="区块高度" width="110" align="center">
                <template #default="{ row }">
                  <span class="mono-text text-blue">{{ row.block_number ? `#${row.block_number}` : '-' }}</span>
                </template>
              </el-table-column>

              <el-table-column label="链网络" width="140" align="center">
                <template #default="{ row }">
                  <el-tag :type="isRealChainRecord(row) ? 'success' : 'warning'" effect="plain" size="small">
                    {{ formatChainType(row.chain_type) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="上链状态" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.status)" effect="dark">
                    {{ formatStatus(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="链上校验" width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="getVerifyTagType(row.verify_status)" effect="plain">
                    {{ formatVerifyStatus(row.verify_status) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="校验结果" width="130" align="center">
                <template #default="{ row }">
                  <el-tag :type="getConsistencyTagType(row)" effect="plain">
                    {{ formatConsistencyResult(row) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column prop="created_at" label="存证时间" width="180" />

              <el-table-column label="审计指令" width="190" fixed="right" align="center">
                <template #default="{ row }">
                  <div class="audit-action-row">
                    <el-button
                      class="audit-action-btn"
                      type="primary"
                      link
                      :icon="View"
                      :loading="detailLoading && currentChainRecord?.id === row.id"
                      @click="handleViewChainRecordDetail(row)"
                    >
                      查看凭证
                    </el-button>
                    <el-button
                      v-if="getRelatedTask(row)?.task_id"
                      class="audit-action-btn"
                      type="success"
                      link
                      :icon="DataBoard"
                      @click="goTaskDetail(getRelatedTask(row)?.task_id)"
                    >
                      追溯任务
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrapper">
              <el-pagination background layout="total, prev, pager, next, jumper" :total="chainTotal" :page-size="chainQuery.page_size" :current-page="chainQuery.page" @current-change="handleChainPageChange" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </main>

    <el-dialog v-model="chainDetailVisible" title="区块链底层存证凭证" width="860px" destroy-on-close class="custom-dialog">
      <div v-if="currentChainRecord" class="detail-content">
        <div class="credential-summary">
          <div class="summary-item">
            <div class="summary-label">业务对象</div>
            <div class="summary-value">{{ formatBizType(currentChainRecord.biz_type) }} <span class="mono-text">#{{ currentChainRecord.biz_id || '-' }}</span></div>
          </div>
          <div class="summary-item">
            <div class="summary-label">关联溯源任务</div>
            <div class="summary-value text-blue">
              <template v-if="getRelatedTask(currentChainRecord)">Task <span class="mono-text">#{{ getRelatedTask(currentChainRecord)?.task_id }}</span></template>
              <template v-else>独立存证</template>
            </div>
          </div>
          <div class="summary-item">
            <div class="summary-label">共识状态</div>
            <div class="summary-value">
              <el-tag :type="getStatusTagType(currentChainRecord.status)" effect="dark">
                {{ formatStatus(currentChainRecord.status).toUpperCase() }}
              </el-tag>
            </div>
          </div>
        </div>

        <el-alert class="detail-alert" :title="getCredentialTip(currentChainRecord)" type="info" show-icon :closable="false" />

        <div class="detail-section-title">链上存证凭证</div>
        <div class="credential-grid">
          <div class="credential-row">
            <div class="credential-label">存证编号</div>
            <div class="credential-value">{{ currentChainRecord.anchor_id || `record_${currentChainRecord.id}` }}</div>
            <el-button link type="primary" :icon="DocumentCopy" @click="copyText(currentChainRecord.anchor_id || currentChainRecord.id)">复制</el-button>
          </div>
          <div class="credential-row">
            <div class="credential-label">链网络</div>
            <div class="credential-value">{{ formatChainType(currentChainRecord.chain_type) }}</div>
          </div>
          <div class="credential-row">
            <div class="credential-label">校验状态</div>
            <div class="credential-value">
              <el-tag :type="getVerifyTagType(currentChainRecord.verify_status)" effect="plain">
                {{ formatVerifyStatus(currentChainRecord.verify_status) }}
              </el-tag>
            </div>
          </div>
          <div class="credential-row">
            <div class="credential-label">校验结果</div>
            <div class="credential-value">
              <el-tag :type="getConsistencyTagType(currentChainRecord)" effect="plain">
                {{ formatConsistencyResult(currentChainRecord) }}
              </el-tag>
            </div>
          </div>
          <div class="credential-row">
            <div class="credential-label">内容哈希</div>
            <div class="credential-value">{{ currentChainRecord.content_hash || '-' }}</div>
            <el-button link type="primary" :icon="DocumentCopy" @click="copyText(currentChainRecord.content_hash)">复制</el-button>
          </div>
          <div class="credential-row">
            <div class="credential-label">交易哈希</div>
            <div class="credential-value text-green">{{ currentChainRecord.tx_hash || '-' }}</div>
            <el-button link type="primary" :icon="DocumentCopy" @click="copyText(currentChainRecord.tx_hash)">复制</el-button>
          </div>
          <div class="credential-row">
            <div class="credential-label">区块高度</div>
            <div class="credential-value text-blue"># {{ currentChainRecord.block_number ?? '-' }}</div>
            <el-button link type="primary" :icon="DocumentCopy" @click="copyText(currentChainRecord.block_number)">复制</el-button>
          </div>
          <div class="credential-row">
            <div class="credential-label">合约地址</div>
            <div class="credential-value">{{ currentChainRecord.contract_address || '-' }}</div>
            <el-button link type="primary" :icon="DocumentCopy" @click="copyText(currentChainRecord.contract_address)">复制</el-button>
          </div>
        </div>

        <div class="verify-box mt-4">
          <div class="verify-item"><span class="verify-dot"></span><span>链上仅保存任务结果摘要哈希，不保存原始业务数据或明细记录。</span></div>
          <div class="verify-item"><span class="verify-dot"></span><span>交易哈希、区块高度和合约地址共同构成 FISCO BCOS 联盟链查询凭证。</span></div>
          <div class="verify-item"><span class="verify-dot"></span><span class="text-blue">{{ getChainVerifyText(currentChainRecord) }}</span></div>
        </div>

        <template v-if="currentChainRecord.verify_detail_json">
          <div class="detail-section-title">链上返回详情</div>
          <div class="fl-terminal-box">
            <div class="terminal-header">
              <div class="mac-dots"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></div>
              <span class="terminal-title">fisco_anchor_response.json</span>
              <el-button link class="copy-btn" @click="copyText(formatJson(currentChainRecord.verify_detail_json))">Copy</el-button>
            </div>
            <div class="terminal-body scrollable"><pre class="json-text">{{ formatJson(currentChainRecord.verify_detail_json) }}</pre></div>
          </div>
        </template>

        <template v-if="currentChainRecord.error_message">
          <div class="detail-section-title">异常回退信息</div>
          <el-alert :title="currentChainRecord.error_message" type="error" show-icon :closable="false" />
        </template>
      </div>
      <template #footer><el-button @click="chainDetailVisible = false">关闭验证</el-button></template>
    </el-dialog>

    <el-dialog v-model="auditDetailVisible" title="全链路行为审计追踪" width="1000px" destroy-on-close class="custom-dialog">
      <div class="audit-link-dialog">
        <div v-if="currentAuditChainRecord" class="audit-link-summary">
          <div><span class="audit-link-label">存证锚点：</span> <span class="mono-text">#{{ currentAuditChainRecord.id }}</span></div>
          <div><span class="audit-link-label">业务对象：</span> <el-tag size="small">{{ formatBizType(currentAuditChainRecord.biz_type) }}</el-tag> <span class="mono-text text-blue">#{{ currentAuditChainRecord.biz_id || '-' }}</span></div>
          <div v-if="getRelatedTask(currentAuditChainRecord)">
            <span class="audit-link-label">溯源计算任务：</span>
            <el-button type="primary" link :icon="Connection" @click="goTaskDetail(getRelatedTask(currentAuditChainRecord)?.task_id)">
              跳转至任务空间 <span class="mono-text">#{{ getRelatedTask(currentAuditChainRecord)?.task_id }}</span>
            </el-button>
          </div>
        </div>

        <el-table v-loading="auditLinkLoading" :data="relatedAuditLogs" border stripe>
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="audit-expand">
                <div class="fl-terminal-box">
                  <div class="terminal-header">
                    <div class="mac-dots"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></div>
                    <span class="terminal-title">bash - payload_request.json</span>
                    <el-button link class="copy-btn" @click="copyText(formatJson(row.request_json))">Copy</el-button>
                  </div>
                  <div class="terminal-body scrollable"><pre class="json-text">{{ formatJson(row.request_json) }}</pre></div>
                </div>

                <div class="fl-terminal-box">
                  <div class="terminal-header">
                    <div class="mac-dots"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></div>
                    <span class="terminal-title">bash - callback_result.json</span>
                    <el-button link class="copy-btn" @click="copyText(formatJson(row.result_json))">Copy</el-button>
                  </div>
                  <div class="terminal-body scrollable"><pre class="json-text">{{ formatJson(row.result_json) }}</pre></div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="id" label="审计ID" width="90" align="center"><template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template></el-table-column>
          <el-table-column label="动作协议" min-width="180"><template #default="{ row }"><el-tag effect="plain" type="info">{{ formatOperationType(row.operation_type) }}</el-tag></template></el-table-column>
          <el-table-column prop="object_type" label="资源类型" width="130" align="center" />
          <el-table-column prop="operation_desc" label="行为描述" min-width="220" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间戳" width="170" />
        </el-table>
        <el-empty v-if="!auditLinkLoading && relatedAuditLogs.length === 0" description="底层暂无衍生审计流水" />
      </div>
      <template #footer><el-button @click="auditDetailVisible = false">完成审计</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh, Monitor, Link, DataBoard, DocumentCopy, Search,
  RefreshLeft, View, Connection
} from '@element-plus/icons-vue'
import { getDashboardSummaryApi, getRecentAuditLogsApi } from '@/api/dashboard'
import { getChainRecordList, getChainRecordDetail } from '@/api/chainRecord'
import { getAuditLogList, getAuditLogDetail } from '@/api/auditLog'

// --- 保持原有业务逻辑完全不变 ---
const router = useRouter()
const loading = ref(false)
const activeTab = ref('audit')
const summary = ref<any>({})
const auditLogs = ref<any[]>([])
const chainRecords = ref<any[]>([])
const chainTotal = ref(0)

const chainQuery = ref({ page: 1, page_size: 10, biz_type: '', biz_id: '', status: '' })
const detailLoading = ref(false)
const chainDetailVisible = ref(false)
const currentChainRecord = ref<any>(null)
const auditLinkLoading = ref(false)
const auditDetailVisible = ref(false)
const currentAuditChainRecord = ref<any>(null)
const relatedAuditLogs = ref<any[]>([])
const relatedAuditTotal = ref(0)

function unwrapResponse(res: any) { return res?.data?.data ?? res?.data ?? res }

async function loadSummary() {
  const res = await getDashboardSummaryApi()
  summary.value = unwrapResponse(res) || {}
}

async function loadAuditLogs() {
  const res = await getRecentAuditLogsApi(20)
  auditLogs.value = unwrapResponse(res) || []
}

async function loadChainRecords() {
  const params: any = { page: chainQuery.value.page, page_size: chainQuery.value.page_size }
  if (chainQuery.value.biz_type) params.biz_type = chainQuery.value.biz_type
  if (chainQuery.value.biz_id) params.biz_id = chainQuery.value.biz_id
  if (chainQuery.value.status) params.status = chainQuery.value.status

  const res = await getChainRecordList(params)
  const data = unwrapResponse(res) || {}
  chainRecords.value = data.items || []
  chainTotal.value = data.total || 0
}

function handleSearchChainRecords() { chainQuery.value.page = 1; loadChainRecords() }
function handleResetChainRecords() { chainQuery.value = { page: 1, page_size: 10, biz_type: '', biz_id: '', status: '' }; loadChainRecords() }
function handleChainPageChange(page: number) { chainQuery.value.page = page; loadChainRecords() }

async function handleViewChainRecordDetail(row: any) {
  if (!row?.id) { ElMessage.warning('存证记录ID不存在'); return }
  detailLoading.value = true; currentChainRecord.value = row
  try {
    const res = await getChainRecordDetail(row.id)
    currentChainRecord.value = unwrapResponse(res) || row
    chainDetailVisible.value = true
  } catch (error) { ElMessage.error('存证详情加载失败') } finally { detailLoading.value = false }
}

async function queryAuditLogs(params: any) {
  const res = await getAuditLogList(params); const data = unwrapResponse(res) || {}; return { total: data.total || 0, items: data.items || [] }
}

async function querySingleAuditLog(logId: number | string | null | undefined) {
  if (!logId) return []
  try { const res = await getAuditLogDetail(logId); const data = unwrapResponse(res); return data ? [data] : [] } catch (error) { return [] }
}

async function handleViewRelatedAuditLogs(row: any) {
  if (!row?.id) { ElMessage.warning('存证记录ID不存在'); return }
  auditLinkLoading.value = true; currentAuditChainRecord.value = row; relatedAuditLogs.value = []; relatedAuditTotal.value = 0
  try {
    const primary = await queryAuditLogs({ page: 1, page_size: 20, object_type: 'chain_record', object_id: String(row.id) })
    let items = primary.items; let total = primary.total
    if (items.length === 0 && row.biz_type === 'audit_log') { items = await querySingleAuditLog(row.biz_id); total = items.length }
    const relatedTask = getRelatedTask(row)
    if (items.length === 0 && relatedTask?.task_id) {
      const fallback = await queryAuditLogs({ page: 1, page_size: 20, task_id: relatedTask.task_id, operation_type: 'TASK_RESULT_CHAIN_ANCHOR' })
      items = fallback.items; total = fallback.total
    }
    relatedAuditLogs.value = items; relatedAuditTotal.value = total; auditDetailVisible.value = true
  } catch (error) { ElMessage.error('关联审计日志加载失败') } finally { auditLinkLoading.value = false }
}

function getRelatedTask(record: any) { return record?.related_task || null }
function goTaskDetail(taskId: number | string | null | undefined) {
  if (!taskId) { ElMessage.warning('未关联任务'); return }
  chainDetailVisible.value = false; router.push(`/tasks/${taskId}`)
}

function formatBizType(type: string) { const map: Record<string, string> = { task: '任务存证', task_result: '任务结果存证', audit_log: '审计日志存证', resource_operation: '资源操作存证' }; return map[type] || type || '-' }
function formatStatus(status: string) { const map: Record<string, string> = { success: '已上链', failed: '上链失败', pending: '待上链', skipped: '未启用' }; return map[status] || status || '-' }
function formatChainType(type: string) { const map: Record<string, string> = { fisco_bcos: 'FISCO BCOS', mock_fisco_bcos: 'Mock FISCO', local: '本地预留' }; return map[type] || type || '-' }
function isRealChainRecord(record: any) {
  return record?.chain_type === 'fisco_bcos' && !!record?.tx_hash && !!record?.block_number
}

function getChainVerifyText(record: any) {
  if (isChainConsistencyPassed(record)) {
    return '当前记录已完成 FISCO BCOS 真实链上存证，链上摘要与系统存证摘要一致。'
  }
  if (record?.status === 'failed') return '当前记录上链失败，请查看异常回退信息并重新触发任务生成或上链流程。'
  if (record?.chain_type === 'mock_fisco_bcos') return '当前记录为历史 Mock 存证，仅用于开发联调，不作为真实链上凭证。'
  return '当前记录可通过内容哈希、交易哈希和区块高度进行二次核对。'
}

function getStatusTagType(status: string) { if (status === 'success') return 'success'; if (status === 'failed') return 'danger'; if (status === 'pending') return 'warning'; return 'info' }
function formatVerifyStatus(status: string) { const map: Record<string, string> = { success: '校验通过', failed: '校验失败', pending: '待校验' }; return map[status] || '-' }
function getVerifyTagType(status: string) { if (status === 'success') return 'success'; if (status === 'failed') return 'danger'; return 'info' }

function getVerifyDetail(record: any) {
  const detail = record?.verify_detail_json
  if (!detail) return {}
  if (typeof detail === 'string') {
    try { return JSON.parse(detail) } catch { return {} }
  }
  return typeof detail === 'object' ? detail : {}
}

function getChainResultArray(record: any) {
  const detail = getVerifyDetail(record)
  return Array.isArray(detail?.chain_result) ? detail.chain_result : []
}

function isChainConsistencyPassed(record: any) {
  if (!record || record.status !== 'success' || record.verify_status !== 'success') return false
  const chainResult = getChainResultArray(record)

  // 列表接口如果暂未返回 verify_detail_json，则先按链上校验状态和真实交易凭证判断为已校验。
  if (chainResult.length === 0) return isRealChainRecord(record)

  const chainAnchorId = chainResult[0] ? String(chainResult[0]) : ''
  const chainDigest = chainResult[1] ? String(chainResult[1]) : ''
  const localAnchorId = record.anchor_id ? String(record.anchor_id) : ''
  const localDigest = record.content_hash ? String(record.content_hash) : ''

  const digestMatched = !!localDigest && !!chainDigest && localDigest === chainDigest
  const anchorMatched = !localAnchorId || !chainAnchorId || localAnchorId === chainAnchorId
  return digestMatched && anchorMatched
}

function formatConsistencyResult(record: any) {
  if (!record) return '-'
  if (record.status === 'failed') return '上链失败'
  if (record.status === 'pending') return '待上链'
  if (record.status === 'skipped') return '未上链'
  if (record.verify_status === 'failed') return '不一致'
  if (record.verify_status === 'pending') return '待校验'
  if (isChainConsistencyPassed(record)) return '一致'
  if (record.status === 'success') return '待校验'
  return '-'
}

function getConsistencyTagType(record: any) {
  const result = formatConsistencyResult(record)
  if (result === '一致') return 'success'
  if (result === '不一致' || result === '上链失败') return 'danger'
  if (result === '待校验' || result === '待上链') return 'warning'
  return 'info'
}

function shortHash(value: string | null | undefined) {
  if (!value) return '-'
  if (value.length <= 24) return value
  return `${value.slice(0, 10)}......${value.slice(-10)}`
}

function getCredentialTip(record: any) {
  const bizType = record?.biz_type
  if (bizType === 'task_result') return '该凭证由任务执行成功后自动生成，FISCO BCOS 链上保存结果摘要哈希，用于证明任务结果未被篡改。'
  if (bizType === 'task') return '该凭证用于记录任务创建或调度配置摘要，便于后续追溯任务来源。'
  if (bizType === 'resource_operation') return '该凭证记录节点、数据、模板等资源操作摘要，用于后续审计追责。'
  return '该凭证记录系统关键操作摘要，用于事后审计和一致性核对。'
}

function formatOperationType(type: string) {
  const map: Record<string, string> = { TASK_CREATE: '初始化任务空间', TASK_RUN: '触发协同计算流', TASK_RESULT_CHAIN_ANCHOR: '发起链上共识锚定', TASK_PARTY_CREATE: '注册入网节点', TASK_PARTY_UPDATE: '变更节点权限', TASK_PARTY_DELETE: '剥离计算节点' }
  return map[type] || type || '-'
}

function formatJson(value: any) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'string') { try { return JSON.stringify(JSON.parse(value), null, 2) } catch { return value } }
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}

async function copyText(text: string | number | null | undefined) {
  const value = String(text ?? ''); if (!value) { ElMessage.warning('暂无可复制内容'); return }
  try {
    if (navigator?.clipboard?.writeText) { await navigator.clipboard.writeText(value) } else {
      const textarea = document.createElement('textarea'); textarea.value = value; textarea.style.position = 'fixed'; textarea.style.opacity = '0'
      document.body.appendChild(textarea); textarea.select(); document.execCommand('copy'); document.body.removeChild(textarea)
    }
    ElMessage.success('系统回执已复制')
  } catch (error) { ElMessage.error('复制失败') }
}

async function loadAll() {
  loading.value = true
  try { await Promise.all([loadSummary(), loadAuditLogs(), loadChainRecords()]) } catch (error) { ElMessage.error('区块链基座同步失败') } finally { loading.value = false }
}

onMounted(() => { loadAll() })
</script>

<style scoped>
/* 页面骨架 */
.blockchain-page { min-height: 100vh; background: #f0f2f5; padding: 24px; }
.page-header { height: 72px; background: #ffffff; border-bottom: 1px solid #e5e7eb; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; border-radius: 8px; margin-bottom: 20px;}
.title-area h1 { margin: 0; font-size: 20px; color: #1f2937; font-weight: 600; }
.title-area p { margin: 4px 0 0; color: #6b7280; font-size: 13px; }
.mb-4 { margin-bottom: 20px; }

/* 模块标题 */
.section-title { margin: 0 0 16px 0; font-size: 16px; color: #374151; font-weight: 600; border-left: 4px solid #409eff; padding-left: 10px; }

/* 统计卡片 */
.stat-card { border-radius: 8px; border: none; }
.dark-card { background: linear-gradient(135deg, #1f2937 0%, #374151 100%); color: #ffffff; }
.dark-card .stat-label { color: #9ca3af; }
.stat-header { display: flex; justify-content: space-between; align-items: center; }
.stat-label { color: #6b7280; font-size: 14px; }
.stat-value { margin-top: 16px; }

/* 表格与功能条 */
.table-card { border-radius: 8px; border: none; }
.chain-toolbar { margin-bottom: 16px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.pagination-wrapper { margin-top: 16px; display: flex; justify-content: flex-end; }
.custom-tabs :deep(.el-tabs__nav-wrap::after) { height: 1px; background-color: #e5e7eb; }

/* 极客美学组件：Hash 与等宽字体 */
.hash-wrapper { display: inline-flex; align-items: center; gap: 6px; background: #f3f4f6; padding: 4px 10px; border-radius: 6px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s; }
.hash-wrapper:hover { background: #e5e7eb; border-color: #d1d5db; }
.hash-wrapper.w-full { display: flex; width: 100%; justify-content: flex-start; }
.hash-icon { color: #409eff; font-size: 14px; }
.hash-text { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; color: #374151; letter-spacing: 0.5px; }
.mono-text { font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; }
.mono-input :deep(.el-input__inner) { font-family: 'Consolas', 'Monaco', monospace; }
.text-blue { color: #409eff; font-weight: bold; }
.text-green { color: #10b981; font-weight: bold; }

/* 极客美学组件：终端框 (Terminal Box) */
.fl-terminal-box { width: 100%; border-radius: 8px; background: #1e1e1e; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); margin-top: 10px; display: flex; flex-direction: column;}
.terminal-header { background: #2d2d2d; padding: 8px 12px; display: flex; align-items: center; border-bottom: 1px solid #404040; position: relative; }
.mac-dots { display: flex; gap: 6px; margin-right: 12px; }
.mac-dots .dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.red { background: #ff5f56; } .dot.yellow { background: #ffbd2e; } .dot.green { background: #27c93f; }
.terminal-title { color: #a0a0a0; font-family: 'Consolas', monospace; font-size: 12px; }
.terminal-header .copy-btn { position: absolute; right: 12px; color: #569cd6; font-size: 12px; font-family: Consolas; }
.terminal-body { padding: 16px; color: #d4d4d4; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6; max-height: 300px; overflow-y: auto; background: #1e1e1e;}
.terminal-body pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; font-family: 'Consolas', monospace; }

/* 详情弹窗样式 */
.detail-content { padding: 4px 0; }
.credential-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.summary-item { padding: 14px; border: 1px solid #e5e7eb; border-radius: 8px; background: #ffffff; }
.summary-label { margin-bottom: 8px; color: #8a96a8; font-size: 12px; }
.summary-value { color: #1f2937; font-size: 14px; font-weight: 600; word-break: break-all; }
.detail-alert { margin-bottom: 16px; }
.detail-section-title { margin: 18px 0 10px; color: #1f2937; font-size: 15px; font-weight: 600; border-left: 3px solid #67C23A; padding-left: 8px;}

/* 链上凭证 Grid */
.credential-grid { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #ffffff;}
.credential-row { display: flex; align-items: center; gap: 10px; padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 13px; }
.credential-row:last-child { border-bottom: none; }
.credential-label { width: 80px; flex-shrink: 0; color: #6b7280; }
.credential-value { flex: 1; min-width: 0; color: #1f2937; word-break: break-all; font-family: 'Consolas', monospace; }

/* 校验盒子 */
.verify-box { padding: 14px; border: 1px solid #c2e7b0; border-radius: 8px; background: #f0f9eb; }
.verify-item { display: flex; align-items: flex-start; gap: 8px; color: #606266; font-size: 13px; line-height: 1.8; }
.verify-dot { width: 6px; height: 6px; margin-top: 9px; border-radius: 50%; background: #67c23a; flex-shrink: 0; }
.mt-4 { margin-top: 16px; }

/* 关联审计弹窗 */
.audit-link-summary { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 16px; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #ffffff; color: #1f2937; font-size: 14px; }
.audit-link-label { color: #8a96a8; font-weight: 600;}
.audit-expand { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: 12px 24px; background: #f9fafc; border-top: 1px dashed #ebeef5; border-bottom: 1px dashed #ebeef5;}

/* 审计指令按钮：同一行展示，避免上下换行 */
.audit-action-row {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  white-space: nowrap;
  width: 100%;
}
.audit-action-row :deep(.el-button) {
  margin-left: 0;
}
.audit-action-btn {
  padding: 0;
}

.muted-hash { color: #9ca3af; cursor: default; }

</style>