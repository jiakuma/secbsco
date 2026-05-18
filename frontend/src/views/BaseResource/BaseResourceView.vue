<template>
  <div class="base-resource-view">
    <div class="page-header">
      <div>
        <h2>基础资源管理</h2>
        <p>统一维护机构、用户与节点资源，为群组协作、任务调度和可信审计提供基础资源底座。</p>
      </div>
    </div>

    <el-row :gutter="12" class="summary-row">
      <el-col :xs="12" :sm="8" :md="6">
        <div class="summary-card">
          <div class="summary-value">{{ agencyTotal }}</div>
          <div class="summary-label">机构总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6">
        <div class="summary-card">
          <div class="summary-value">{{ userTotal }}</div>
          <div class="summary-label">用户总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6">
        <div class="summary-card">
          <div class="summary-value">{{ nodeTotal }}</div>
          <div class="summary-label">节点总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="8" :md="6">
        <div class="summary-card">
          <div class="summary-value">{{ activeNodeTotal }}</div>
          <div class="summary-label">启用节点</div>
        </div>
      </el-col>
    </el-row>

    <el-card class="main-card" shadow="never">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="机构管理" name="agencies">
          <AgencyManagePanel @summary-change="handleAgencySummary" />
        </el-tab-pane>
        <el-tab-pane label="用户管理" name="users">
          <UserManagePanel @summary-change="handleUserSummary" />
        </el-tab-pane>
        <el-tab-pane label="节点管理" name="nodes">
          <NodeManagePanel @summary-change="handleNodeSummary" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AgencyManagePanel from './components/AgencyManagePanel.vue'
import UserManagePanel from './components/UserManagePanel.vue'
import NodeManagePanel from './components/NodeManagePanel.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref('agencies')
const agencyTotal = ref(0)
const userTotal = ref(0)
const nodeTotal = ref(0)
const activeNodeTotal = ref(0)

function normalizeTab(tab: any) {
  if (tab === 'user') return 'users'
  if (tab === 'agency') return 'agencies'
  if (tab === 'node') return 'nodes'
  if (['agencies', 'users', 'nodes'].includes(String(tab))) return String(tab)
  return 'agencies'
}

function syncTabFromRoute() {
  activeTab.value = normalizeTab(route.query.tab)
}

function handleTabChange(tabName: any) {
  router.replace({ path: '/base-resource', query: { tab: String(tabName) } })
}

function handleAgencySummary(payload: { total: number }) {
  agencyTotal.value = payload.total || 0
}

function handleUserSummary(payload: { total: number }) {
  userTotal.value = payload.total || 0
}

function handleNodeSummary(payload: { total: number; active: number }) {
  nodeTotal.value = payload.total || 0
  activeNodeTotal.value = payload.active || 0
}

onMounted(syncTabFromRoute)
watch(() => route.query.tab, syncTabFromRoute)
</script>

<style scoped>
.base-resource-view {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #0f172a;
}

.page-header p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.summary-row {
  margin-bottom: 14px;
}

.summary-card {
  padding: 18px 18px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.summary-value {
  font-size: 25px;
  font-weight: 800;
  color: #0f172a;
}

.summary-label {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.main-card {
  border-radius: 14px;
}
</style>
