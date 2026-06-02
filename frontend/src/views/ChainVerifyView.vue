<template>
  <div class="chain-verify-page">
    <header class="page-header">
      <div>
        <h1>链上校验</h1>
        <p>通过存证记录、内容哈希和交易哈希核对 FISCO BCOS 链上凭证一致性。</p>
      </div>
    </header>

    <el-card shadow="never" class="verify-card">
      <template #header>
        <div class="card-header">
          <span>存证凭证校验</span>
          <el-tag type="success" effect="plain">FISCO BCOS</el-tag>
        </div>
      </template>

      <el-form :model="verifyForm" label-width="110px" class="verify-form">
        <el-form-item label="存证记录ID" required>
          <el-input
            v-model="verifyForm.recordId"
            placeholder="请输入 chain_record.id，例如 246"
            clearable
            class="mono-input"
          />
        </el-form-item>

        <el-form-item label="内容哈希">
          <el-input
            v-model="verifyForm.contentHash"
            placeholder="可选：输入待核对的 result_hash / content_hash"
            clearable
            class="mono-input"
          />
        </el-form-item>

        <el-form-item label="交易哈希">
          <el-input
            v-model="verifyForm.txHash"
            placeholder="可选：输入待核对的 tx_hash"
            clearable
            class="mono-input"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleVerify">开始校验</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="verifyResult" shadow="never" class="result-card">
      <template #header>
        <div class="card-header">
          <span>校验结果</span>
          <el-tag :type="verifyResult.passed ? 'success' : 'danger'" effect="dark">
            {{ verifyResult.passed ? '校验通过' : '校验未通过' }}
          </el-tag>
        </div>
      </template>

      <el-alert
        :title="verifyResult.message"
        :type="verifyResult.passed ? 'success' : 'error'"
        show-icon
        :closable="false"
        class="mb-4"
      />

      <div class="credential-grid">
        <div class="credential-row">
          <span class="credential-label">存证ID</span>
          <span class="credential-value mono-text">#{{ currentRecord?.id || '-' }}</span>
        </div>
        <div class="credential-row">
          <span class="credential-label">业务类型</span>
          <span class="credential-value">{{ formatBizType(currentRecord?.biz_type) }}</span>
        </div>
        <div class="credential-row">
          <span class="credential-label">业务对象</span>
          <span class="credential-value mono-text">{{ currentRecord?.biz_id || '-' }}</span>
        </div>
        <div class="credential-row">
          <span class="credential-label">存证编号</span>
          <span class="credential-value mono-text">{{ currentRecord?.anchor_id || '-' }}</span>
        </div>
        <div class="credential-row">
          <span class="credential-label">内容哈希</span>
          <span class="credential-value mono-text">{{ currentRecord?.content_hash || '-' }}</span>
          <el-button link type="primary" @click="copyText(currentRecord?.content_hash)">复制</el-button>
        </div>
        <div class="credential-row">
          <span class="credential-label">交易哈希</span>
          <span class="credential-value mono-text text-green">{{ currentRecord?.tx_hash || '-' }}</span>
          <el-button link type="primary" @click="copyText(currentRecord?.tx_hash)">复制</el-button>
        </div>
        <div class="credential-row">
          <span class="credential-label">区块高度</span>
          <span class="credential-value mono-text text-blue">{{ currentRecord?.block_number ? `#${currentRecord.block_number}` : '-' }}</span>
        </div>
        <div class="credential-row">
          <span class="credential-label">合约地址</span>
          <span class="credential-value mono-text">{{ currentRecord?.contract_address || '-' }}</span>
          <el-button link type="primary" @click="copyText(currentRecord?.contract_address)">复制</el-button>
        </div>
        <div class="credential-row">
          <span class="credential-label">上链状态</span>
          <span class="credential-value">
            <el-tag :type="getStatusTagType(currentRecord?.status)" effect="plain">
              {{ formatStatus(currentRecord?.status) }}
            </el-tag>
          </span>
        </div>
        <div class="credential-row">
          <span class="credential-label">链上校验</span>
          <span class="credential-value">
            <el-tag :type="getVerifyTagType(currentRecord?.verify_status)" effect="plain">
              {{ formatVerifyStatus(currentRecord?.verify_status) }}
            </el-tag>
          </span>
        </div>
      </div>

      <div v-if="currentRecord?.verify_detail_json" class="terminal-box">
        <div class="terminal-header">
          <span>fisco_anchor_response.json</span>
          <el-button link type="primary" @click="copyText(formatJson(currentRecord?.verify_detail_json))">复制</el-button>
        </div>
        <pre>{{ formatJson(currentRecord?.verify_detail_json) }}</pre>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getChainRecordDetail } from '@/api/chainRecord'

const loading = ref(false)
const currentRecord = ref<any>(null)
const verifyResult = ref<{ passed: boolean; message: string } | null>(null)

const verifyForm = ref({
  recordId: '',
  contentHash: '',
  txHash: '',
})

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

function normalize(value: any) {
  return String(value ?? '').trim()
}

function formatBizType(type: string) {
  const map: Record<string, string> = {
    task: '任务存证',
    task_result: '任务结果存证',
    audit_log: '审计日志存证',
    resource_operation: '资源操作存证',
  }
  return map[type] || type || '-'
}

function formatStatus(status: string) {
  const map: Record<string, string> = {
    success: '已上链',
    failed: '上链失败',
    pending: '待上链',
    skipped: '未启用',
  }
  return map[status] || status || '-'
}

function getStatusTagType(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'pending') return 'warning'
  return 'info'
}

function formatVerifyStatus(status: string) {
  const map: Record<string, string> = {
    success: '校验通过',
    failed: '校验失败',
    pending: '待校验',
  }
  return map[status] || '-'
}

function getVerifyTagType(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}

function formatJson(value: any) {
  if (value === null || value === undefined || value === '') return '-'
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
    await navigator.clipboard.writeText(value)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

async function handleVerify() {
  const recordId = normalize(verifyForm.value.recordId)
  if (!recordId) {
    ElMessage.warning('请先输入存证记录ID')
    return
  }

  loading.value = true
  verifyResult.value = null
  currentRecord.value = null

  try {
    const res = await getChainRecordDetail(Number(recordId))
    const record = unwrapResponse(res)
    currentRecord.value = record

    const errors: string[] = []

    if (record?.status !== 'success') {
      errors.push('存证状态不是已上链')
    }

    if (record?.verify_status && record.verify_status !== 'success') {
      errors.push('链上校验状态不是通过')
    }

    const inputHash = normalize(verifyForm.value.contentHash)
    if (inputHash && inputHash !== normalize(record?.content_hash)) {
      errors.push('输入内容哈希与存证记录不一致')
    }

    const inputTxHash = normalize(verifyForm.value.txHash)
    if (inputTxHash && inputTxHash !== normalize(record?.tx_hash)) {
      errors.push('输入交易哈希与存证记录不一致')
    }

    if (!record?.tx_hash || !record?.block_number || !record?.contract_address) {
      errors.push('链上交易哈希、区块高度或合约地址不完整')
    }

    verifyResult.value = {
      passed: errors.length === 0,
      message: errors.length === 0
        ? '校验通过：存证记录、链上交易信息与输入凭证一致。'
        : `校验未通过：${errors.join('；')}。`,
    }
  } catch (error) {
    verifyResult.value = {
      passed: false,
      message: '校验失败：未查询到该存证记录或接口返回异常。',
    }
    ElMessage.error('链上校验失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  verifyForm.value = {
    recordId: '',
    contentHash: '',
    txHash: '',
  }
  verifyResult.value = null
  currentRecord.value = null
}
</script>

<style scoped>
.chain-verify-page {
  min-height: 100%;
  padding: 24px;
  background: #f5f7fb;
}

.page-header {
  margin-bottom: 16px;
}

.page-header h1 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 24px;
  font-weight: 700;
}

.page-header p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.verify-card,
.result-card {
  margin-bottom: 16px;
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #1f2937;
  font-weight: 600;
}

.verify-form {
  max-width: 820px;
}

.mono-input :deep(.el-input__inner),
.mono-text {
  font-family: Consolas, Monaco, monospace;
}

.mb-4 {
  margin-bottom: 16px;
}

.credential-grid {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.credential-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.credential-row:last-child {
  border-bottom: none;
}

.credential-label {
  width: 96px;
  flex-shrink: 0;
  color: #6b7280;
  font-weight: 600;
}

.credential-value {
  flex: 1;
  min-width: 0;
  color: #1f2937;
  word-break: break-all;
}

.text-green {
  color: #059669;
}

.text-blue {
  color: #2563eb;
}

.terminal-box {
  margin-top: 16px;
  overflow: hidden;
  border: 1px solid #1f2937;
  border-radius: 10px;
  background: #0f172a;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  color: #d1d5db;
  border-bottom: 1px solid #334155;
  font-size: 13px;
}

.terminal-box pre {
  max-height: 320px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
