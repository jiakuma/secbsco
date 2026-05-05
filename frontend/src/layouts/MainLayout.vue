<template>
  <div class="main-layout">
    <aside class="side-nav">
      <div class="brand">
        <div class="brand-logo">联</div>
        <div>
          <div class="brand-title">联合统计系统</div>
          <div class="brand-subtitle">可信协同 · 隐私计算</div>
        </div>
      </div>

      <el-menu
        router
        :default-active="activeMenu"
        class="side-menu"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <span class="menu-icon">⌂</span>
          <span>首页总览</span>
        </el-menu-item>

        <el-menu-item index="/tasks">
          <span class="menu-icon">▣</span>
          <span>联合任务</span>
        </el-menu-item>

        <el-menu-item index="/nodes">
          <span class="menu-icon">◎</span>
          <span>节点资源</span>
        </el-menu-item>

        <el-menu-item index="/blockchain">
          <span class="menu-icon">◇</span>
          <span>区块链治理</span>
        </el-menu-item>
      </el-menu>

    </aside>

    <main class="main-content">
      <header class="layout-header">
        <div class="layout-title">
          {{ route.meta.title || '系统页面' }}
        </div>

        <div class="layout-user">
          <span class="username">{{ username }}</span>
          <el-button size="small" @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </header>

      <section class="layout-body">
        <router-view />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/tasks')) return '/tasks'
  if (route.path.startsWith('/nodes')) return '/nodes'
  if (route.path.startsWith('/blockchain')) return '/blockchain'
  return '/dashboard'
})

const username = computed(() => {
  return authStore.userInfo?.username || authStore.userInfo?.real_name || '当前用户'
})

async function handleLogout() {
  await authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  background: #f5f7fb;
}

.side-nav {
  width: 220px;
  min-height: 100vh;
  background: #0f172a;
  display: flex;
  flex-direction: column;
  color: #ffffff;
}

.brand {
  height: 72px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.side-menu {
  flex: 1;
  border-right: none;
  padding-top: 12px;
}

.side-menu :deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 10px;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: #2563eb;
}

.menu-icon {
  width: 22px;
  display: inline-block;
  margin-right: 8px;
  text-align: center;
}

.side-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-name {
  margin-bottom: 10px;
  font-size: 13px;
  color: #cbd5e1;
}

.main-content {
  flex: 1;
  min-width: 0;
  min-height: 100vh;
  background: #f5f7fb;
  display: flex;
  flex-direction: column;
}

.layout-header {
  height: 56px;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.layout-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.layout-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  font-size: 14px;
  color: #4b5563;
}

.layout-body {
  flex: 1;
  overflow: auto;
}
</style>