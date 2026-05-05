<template>
  <div class="node-resource-page">
    <div class="page-header">
      <div>
        <h2>节点资源</h2>
        <p>统一查看参与机构、计算节点与本地数据资源目录</p>
      </div>

      <el-button type="primary" :loading="loading" @click="loadAll">
        刷新
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">机构数量</div>
          <div class="stat-value">{{ agencyList.length }}</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">节点数量</div>
          <div class="stat-value">{{ nodeList.length }}</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">数据资源数量</div>
          <div class="stat-value">{{ datasetList.length }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="机构" name="agency">
          <el-table :data="agencyList" border stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="机构编码" min-width="160">
              <template #default="{ row }">
                {{ row.agency_code || row.code || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="机构名称" min-width="200">
              <template #default="{ row }">
                {{ row.agency_name || row.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status || 'active' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="节点" name="node">
          <el-table :data="nodeList" border stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="节点编码" min-width="160">
              <template #default="{ row }">
                {{ row.node_code || row.code || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="节点名称" min-width="200">
              <template #default="{ row }">
                {{ row.node_name || row.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="agency_id" label="所属机构ID" width="120" />
            <el-table-column label="节点类型" width="140">
              <template #default="{ row }">
                {{ row.node_type || row.type || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status || 'active' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="数据资源" name="dataset">
          <el-table :data="datasetList" border stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column label="资源编码" min-width="160">
              <template #default="{ row }">
                {{ row.dataset_code || row.code || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="资源名称" min-width="200">
              <template #default="{ row }">
                {{ row.dataset_name || row.name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="agency_id" label="所属机构ID" width="120" />
            <el-table-column label="数据类型" width="140">
              <template #default="{ row }">
                {{ row.data_type || row.dataset_type || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status || 'active' }}
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
import { getAgencyList } from '@/api/agency'
import { getNodeList } from '@/api/node'
import { getDatasetList } from '@/api/dataset'

const loading = ref(false)
const activeTab = ref('agency')

const agencyList = ref<any[]>([])
const nodeList = ref<any[]>([])
const datasetList = ref<any[]>([])

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
  if (status === 'active' || status === 'online' || status === 'success') return 'success'
  if (status === 'inactive' || status === 'offline') return 'info'
  if (status === 'failed' || status === 'error') return 'danger'
  return 'info'
}

async function loadAgencies() {
  const res = await getAgencyList({
    page: 1,
    page_size: 100,
  })

  agencyList.value = normalizeList(unwrapResponse(res))
}

async function loadNodes() {
  const res = await getNodeList({
    page: 1,
    page_size: 100,
  })

  nodeList.value = normalizeList(unwrapResponse(res))
}

async function loadDatasets() {
  const res = await getDatasetList({
    page: 1,
    page_size: 100,
  })

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
  } catch (error) {
    console.error(error)
    ElMessage.error('节点资源数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.node-resource-page {
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