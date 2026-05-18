<template>
  <div class="main-layout">
    <!-- 左侧导航 -->
    <aside class="side-nav">
      <div class="brand">
        <div class="brand-title">生物数据安全的隐私计算系统</div>
      </div>

      <!-- 开发阶段用户切换 -->
      <div class="role-switcher">
        <el-dropdown
          trigger="click"
          :disabled="devUserSwitchLoading"
          @command="handleDevUserChange"
        >
          <button class="role-dropdown-trigger" type="button">
            <span>{{ currentRoleLabel }}</span>
            <span class="role-arrow">▼</span>
          </button>

          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="user in devUsers"
                :key="user.username"
                :command="user.username"
              >
                {{ user.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 一级菜单 -->
      <el-menu
        router
        :default-active="activeMenu"
        class="side-menu"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
      >
        <el-menu-item
          v-for="menu in sidebarMenus"
          :key="menu.path"
          :index="menu.path"
        >
          <span class="menu-icon">{{ menu.icon }}</span>
          <span class="menu-title">{{ menu.title }}</span>
        </el-menu-item>
      </el-menu>

      <!-- 底部退出 -->
      <div class="side-footer">
        <el-button size="small" class="logout-btn" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </aside>

    <!-- 右侧主体 -->
    <main class="main-content">
      <header class="layout-header">
        <div class="header-left">
          <div class="breadcrumb-line">
            <span>首页</span>
            <span class="breadcrumb-separator">/</span>
            <span>{{ currentTitle }}</span>
          </div>
          <div class="layout-title">{{ currentTitle }}</div>
        </div>

        <div class="header-right">
          <div class="header-group" v-if="authStore.currentGroupName">
            <span class="header-label">群组</span>
            <span class="header-value">{{ authStore.currentGroupName }}</span>
          </div>

          <div class="header-user">
            <span class="header-label">当前用户</span>
            <span class="header-value">{{ authStore.displayName }}</span>
          </div>

          <el-tag
            v-for="role in headerRoles"
            :key="`top-${role.role_code}-${role.scope_type}-${role.scope_id}`"
            :type="getRoleTagType(role.role_code)"
            size="small"
            effect="light"
          >
            {{ getRoleLabel(role) }}
          </el-tag>
        </div>
      </header>

      <section class="layout-body">
        <router-view :key="route.fullPath" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

interface SidebarMenuItem {
  title: string
  path: string
  icon: string
}

interface DevUserItem {
  label: string
  username: string
  password: string
  redirectPath: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const devUserSwitchLoading = ref(false)

const devUsers: DevUserItem[] = [
  {
    label: '平台管理员',
    username: 'platform_admin',
    password: '123456',
    redirectPath: '/base-resource',
  },
  {
    label: '国家级机构管理员',
    username: 'national_agency_admin',
    password: '123456',
    redirectPath: '/base-resource',
  },
  {
    label: '省级机构管理员',
    username: 'hebei_agency_admin',
    password: '123456',
    redirectPath: '/base-resource',
  },
  {
    label: '市级机构管理员',
    username: 'shijiazhuang_agency_admin',
    password: '123456',
    redirectPath: '/base-resource',
  },
  {
    label: '业务用户',
    username: 'changan_business_user',
    password: '123456',
    redirectPath: '/tasks',
  },
  {
    label: '治理员',
    username: 'hebei_governor',
    password: '123456',
    redirectPath: '/tasks',
  },
]

const adminMenus: SidebarMenuItem[] = [
  { title: '首页总览', path: '/dashboard', icon: '⌂' },
  { title: '基础资源管理', path: '/base-resource', icon: '▦' },
  { title: '数据资产管理', path: '/data-assets', icon: '▤' },
  { title: '群组协作管理', path: '/groups', icon: '◇' },
  { title: '任务管理', path: '/tasks', icon: '▣' },
]

const userMenus: SidebarMenuItem[] = [
  { title: '任务管理', path: '/tasks', icon: '▣' },
]

const governorMenus: SidebarMenuItem[] = [
  { title: '任务管理', path: '/tasks', icon: '▣' },
  { title: '可信审计管理', path: '/audit', icon: '▨' },
]

const currentTitle = computed(() => {
  return String(route.meta.title || '系统页面')
})

const hasAdminRole = computed(() => {
  return authStore.roles.some((r) => r.role_code === 'admin')
})

const hasGovernorRole = computed(() => {
  return authStore.roles.some((r) => r.role_code === 'governor')
})

const sidebarMenus = computed(() => {
  if (hasAdminRole.value) return adminMenus
  if (hasGovernorRole.value) return governorMenus
  return userMenus
})

const activeMenu = computed(() => {
  const currentPath = route.path

  const prefixMap: Record<string, string> = {
    '/dashboard': '/dashboard',
    '/base-resource': '/base-resource',
    '/base-resource/': '/base-resource',
    '/user-manage': '/base-resource',
    '/user-manage/': '/base-resource',
    '/data-assets': '/data-assets',
    '/groups': '/groups',
    '/groups/': '/groups',
    '/tasks': '/tasks',
    '/tasks/': '/tasks',
    '/audit': '/audit',
    '/audit/': '/audit',
  }

  for (const [prefix, menuPath] of Object.entries(prefixMap)) {
    if (currentPath === prefix || currentPath.startsWith(prefix)) {
      return menuPath
    }
  }

  return sidebarMenus.value[0]?.path || '/dashboard'
})

const headerRoles = computed(() => {
  const roles = authStore.roles || []

  if (roles.length <= 2) return roles

  const platform = roles.find((r) => r.role_code === 'admin' && r.scope_type === 'platform')
  if (platform) return [platform]

  return roles.slice(0, 2)
})

const currentRoleLabel = computed(() => {
  const currentUsername = authStore.userInfo?.username
  const matchedDevUser = devUsers.find((user) => user.username === currentUsername)

  if (matchedDevUser) {
    return matchedDevUser.label
  }

  if (authStore.displayName) {
    return authStore.displayName
  }

  const roles = authStore.roles || []

  if (roles.some((r) => r.role_code === 'admin' && r.scope_type === 'platform')) {
    return '平台管理员'
  }
  if (roles.some((r) => r.role_code === 'admin' && r.scope_type === 'agency')) {
    return '机构管理员'
  }
  if (roles.some((r) => r.role_code === 'governor')) {
    return '治理员'
  }
  if (roles.some((r) => r.role_code === 'user')) {
    return '业务用户'
  }

  return '当前用户'
})

function getRoleTagType(roleCode: string): 'success' | 'warning' | 'danger' | 'info' {
  if (roleCode === 'admin') return 'danger'
  if (roleCode === 'governor') return 'warning'
  if (roleCode === 'user') return 'success'
  return 'info'
}

function getRoleLabel(role: any): string {
  if (role.role_code === 'admin' && role.scope_type === 'platform') return '平台管理员'
  if (role.role_code === 'admin' && role.scope_type === 'agency') return '机构管理员'
  if (role.role_code === 'user') return '业务用户'
  if (role.role_code === 'governor') return '治理员'

  const scopeLabels: Record<string, string> = {
    platform: '平台',
    agency: '机构',
    group: '群组',
  }
  const roleLabels: Record<string, string> = {
    admin: '管理员',
    user: '业务用户',
    governor: '治理员',
  }
  const scope = scopeLabels[role.scope_type] || role.scope_type
  const roleName = roleLabels[role.role_code] || role.role_code
  return `${scope}${roleName}`
}

async function handleDevUserChange(username: string) {
  const targetUser = devUsers.find((u) => u.username === username)
  if (!targetUser) return

  try {
    devUserSwitchLoading.value = true

    await authStore.login({
      username: targetUser.username,
      password: targetUser.password,
    })

    ElMessage.success(`已切换为${targetUser.label}`)
    router.push(targetUser.redirectPath)
  } catch (error: any) {
    ElMessage.error(
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      '切换用户失败，请确认测试账号和密码是否正确',
    )
  } finally {
    devUserSwitchLoading.value = false
  }
}

async function handleLogout() {
  await authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(async () => {
  if (authStore.isLogin && !authStore.userInfo) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      authStore.clearAuth()
      router.push('/login')
    }
  }

  if (authStore.isLogin && (!authStore.menus || authStore.menus.length === 0)) {
    try {
      await authStore.fetchMenus()
    } catch (error) {
      // 菜单加载失败时交给页面鉴权处理
    }
  }
})
</script>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  height: 100%;
  margin: 0;
  overflow: hidden;
}

.main-layout {
  height: 100vh;
  display: flex;
  background: #f5f7fb;
  overflow: hidden;
}

/* ===============================
   左侧导航
   =============================== */
.side-nav {
  width: 232px;
  height: 100vh;
  background: #0f172a;
  display: flex;
  flex-direction: column;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 8px 0 24px rgba(15, 23, 42, 0.08);
}

.brand {
  min-height: 82px;
  padding: 18px 18px 14px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-title {
  font-size: 17px;
  line-height: 1.45;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: 0.2px;
}

.role-switcher {
  padding: 16px 14px 10px;
}

.role-dropdown-trigger {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 10px;
  background: rgba(30, 41, 59, 0.88);
  color: #f8fafc;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.role-dropdown-trigger:hover {
  border-color: rgba(96, 165, 250, 0.65);
  background: rgba(30, 64, 175, 0.36);
}

.role-arrow {
  font-size: 10px;
  color: #94a3b8;
}

.side-menu {
  flex: 1;
  border-right: none;
  padding: 8px 8px 12px;
  overflow-y: auto;
}

.side-menu::-webkit-scrollbar {
  width: 4px;
}

.side-menu::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.25);
  border-radius: 999px;
}

.side-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 5px 0;
  padding: 0 14px !important;
  border-radius: 12px;
  font-size: 14px;
  color: #cbd5e1;
}

.side-menu :deep(.el-menu-item:hover) {
  background: rgba(37, 99, 235, 0.16);
  color: #ffffff;
}

.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  color: #ffffff;
  box-shadow: 0 10px 18px rgba(37, 99, 235, 0.25);
}

.menu-icon {
  width: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  font-size: 14px;
}

.menu-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.logout-btn {
  width: 100%;
  height: 34px;
  border: none;
  color: #64748b;
  background: #ffffff;
}

.logout-btn:hover {
  color: #2563eb;
  background: #f8fafc;
}

/* ===============================
   主体区域
   =============================== */
.main-content {
  flex: 1;
  min-width: 0;
  height: 100vh;
  background: #f5f7fb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.layout-header {
  height: 64px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}

.header-left {
  min-width: 0;
}

.breadcrumb-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.breadcrumb-separator {
  color: #cbd5e1;
}

.layout-title {
  font-size: 17px;
  font-weight: 700;
  color: #111827;
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  min-width: 0;
}

.header-group,
.header-user {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 280px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.header-label {
  font-size: 12px;
  color: #94a3b8;
}

.header-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #334155;
  font-weight: 600;
}

.layout-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #f5f7fb;
}

.layout-body :deep(> *) {
  min-height: 100%;
}

@media (max-width: 1200px) {
  .side-nav {
    width: 216px;
  }

  .header-group {
    display: none;
  }
}

@media (max-width: 900px) {
  .header-user {
    display: none;
  }
}
</style>
