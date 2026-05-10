<template>
  <div class="node-resource-page">
    <header class="page-header">
      <div class="title-area">
        <h1>联邦资源拓扑管理</h1>
        <p>统一全网视图，查看参与机构、可信计算节点与本地数据资产目录</p>
      </div>

      <div class="header-actions">
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadAll">
          刷新全网资源
        </el-button>
      </div>
    </header>

    <main class="page-content">
      <el-row :gutter="16" class="mb-4">
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">入网机构总数</span>
              <el-icon :size="20" color="#409EFF"><OfficeBuilding /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="agencyList.length" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">可信计算节点</span>
              <el-icon :size="20" color="#67C23A"><Connection /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="nodeList.length" />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-header">
              <span class="stat-label">注册数据资产</span>
              <el-icon :size="20" color="#E6A23C"><DataLine /></el-icon>
            </div>
            <div class="stat-value">
              <el-statistic :value="datasetList.length" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <h3 class="section-title">资源目录大盘</h3>
      <el-card shadow="never" class="table-card">
        <el-tabs v-model="activeTab" class="custom-tabs">
          <el-tab-pane label="协作机构" name="agency">
            <el-table :data="agencyList" border stripe>
              <el-table-column prop="id" label="系统 ID" width="90" align="center">
                <template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template>
              </el-table-column>
              <el-table-column label="机构标识编码 (Agency Code)" min-width="220">
                <template #default="{ row }">
                  <div class="hash-wrapper" title="点击复制" @click="copyText(row.agency_code || row.code)">
                    <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                    <span class="hash-text">{{ row.agency_code || row.code || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="机构名称" min-width="200">
                <template #default="{ row }">
                  <strong>{{ row.agency_name || row.name || '-' }}</strong>
                </template>
              </el-table-column>
              <el-table-column label="网络状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" effect="dark" size="small">
                    {{ (row.status || 'ACTIVE').toUpperCase() }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="接入时间" width="180" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="计算节点" name="node">
            <el-table :data="nodeList" border stripe>
              <el-table-column prop="id" label="系统 ID" width="90" align="center">
                <template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template>
              </el-table-column>
              <el-table-column label="节点网络标识 (Node Code)" min-width="220">
                <template #default="{ row }">
                  <div class="hash-wrapper" title="点击复制" @click="copyText(row.node_code || row.code)">
                    <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                    <span class="hash-text">{{ row.node_code || row.code || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="节点别名" min-width="180">
                <template #default="{ row }">
                  {{ row.node_name || row.name || '-' }}
                </template>
              </el-table-column>
              <el-table-column label="归属机构 ID" width="120" align="center">
                <template #default="{ row }"><span class="mono-text text-blue">{{ row.agency_id }}</span></template>
              </el-table-column>
              <el-table-column label="引擎类型" width="140" align="center">
                <template #default="{ row }">
                  <el-tag type="info" effect="plain">{{ row.node_type || row.type || 'Standard' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="节点状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" effect="dark" size="small">
                    {{ (row.status || 'ONLINE').toUpperCase() }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="部署时间" width="180" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="数据资产目录" name="dataset">
            <el-table :data="datasetList" border stripe>
              <el-table-column prop="id" label="系统 ID" width="90" align="center">
                <template #default="{ row }"><span class="mono-text">{{ row.id }}</span></template>
              </el-table-column>
              <el-table-column label="资产寻址凭证 (Dataset Code)" min-width="240">
                <template #default="{ row }">
                  <div class="hash-wrapper" title="点击复制" @click="copyText(row.dataset_code || row.code)">
                    <el-icon class="hash-icon"><DocumentCopy /></el-icon>
                    <span class="hash-text">{{ row.dataset_code || row.code || '-' }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="资产名称" min-width="200">
                <template #default="{ row }">
                  <strong>{{ row.dataset_name || row.name || '-' }}</strong>
                </template>
              </el-table-column>
              <el-table-column label="挂载机构 ID" width="120" align="center">
                <template #default="{ row }"><span class="mono-text text-blue">{{ row.agency_id }}</span></template>
              </el-table-column>
              <el-table-column label="资产格式" width="120" align="center">
                <template #default="{ row }">
                  <el-tag type="warning" effect="plain">{{ row.data_type || row.dataset_type || 'CSV' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="授权状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" effect="dark" size="small">
                    {{ (row.status || 'ACTIVE').toUpperCase() }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="注册时间" width="180" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAgencyList } from '@/api/agency'
import { getNodeList } from '@/api/node'
import { getDatasetList } from '@/api/dataset'

// 引入极客风格图标
import {
  Refresh,
  OfficeBuilding,
  Connection,
  DataLine,
  DocumentCopy
} from '@element-plus/icons-vue'

const loading = ref(false)
const activeTab = ref('agency')

const agencyList = ref<any[]>([])
const nodeList = ref<any[]>([])
const datasetList = ref<any[]>([])

// 实用工具：复制到剪贴板
async function copyText(text: string) {
  if (!text || text === '-') return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('编码凭证已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

function unwrapResponse(res: any) {
  return res?.data?.data ?? res?.data ?? res
}

function normalizeList(payload: any) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.list)) return payload.list
  if (Array.isArray(payload?.records)) return payload.records
  return []
}

function getStatusType(status: string) {
  const s = (status || '').toLowerCase()
  if (['active', 'online', 'success'].includes(s)) return 'success'
  if (['inactive', 'offline'].includes(s)) return 'info'
  if (['failed', 'error'].includes(s)) return 'danger'
  return 'success' // 默认给予正常的绿色标签
}

async function loadAgencies() {
  const res = await getAgencyList({ page: 1, page_size: 100 })
  agencyList.value = normalizeList(unwrapResponse(res))
}

async function loadNodes() {
  const res = await getNodeList({ page: 1, page_size: 100 })
  nodeList.value = normalizeList(unwrapResponse(res))
}

async function loadDatasets() {
  const res = await getDatasetList({ page: 1, page_size: 100 })
  datasetList.value = normalizeList(unwrapResponse(res))
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([
      loadAgencies(),
      loadNodes(),
      loadDatasets(),
    ])
    ElMessage.success('全网资源刷新完成')
  } catch (error) {
    console.error(error)
    ElMessage.error('节点资源数据加载失败，请检查网络')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
/* 页面骨架 */
.node-resource-page {
  min-height: 100vh;
  background: #f0f2f5;
}

.page-header {
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

.page-content {
  padding: 24px;
}

.mb-4 {
  margin-bottom: 20px;
}

/* 模块标题 */
.section-title {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #374151;
  font-weight: 600;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

/* 统计卡片 */
.stat-card {
  border-radius: 8px;
  border: none;
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

/* 表格与 Tab 面板 */
.table-card {
  border-radius: 8px;
  border: none;
}

.custom-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #e5e7eb;
}

/* 极客美学：等宽编号与 Hash 样式 */
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

.mono-text {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
}

.text-blue {
  color: #409eff;
  font-weight: bold;
}
</style>