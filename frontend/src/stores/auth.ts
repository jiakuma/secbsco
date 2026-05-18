// Pinia 登录状态管理
import { defineStore } from 'pinia'
import { loginApi, getMeApi, getMenusApi, logoutApi, type LoginParams } from '@/api/auth'

export interface RoleInfo {
  role_code: string
  scope_type: string
  scope_id: number | null
}

export interface GroupInfoItem {
  group_id: number
  group_code: string
  group_name: string
  status: string
}

export interface MenuItem {
  title: string
  path: string
  icon?: string
}

interface AuthState {
  token: string
  tokenType: string
  userInfo: any | null
  roles: RoleInfo[]
  groups: GroupInfoItem[]
  permissions: string[]
  menus: MenuItem[]
  currentGroupId: number | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('access_token') || '',
    tokenType: localStorage.getItem('token_type') || 'bearer',
    userInfo: localStorage.getItem('user_info')
      ? JSON.parse(localStorage.getItem('user_info') as string)
      : null,
    roles: localStorage.getItem('user_roles')
      ? JSON.parse(localStorage.getItem('user_roles') as string)
      : [],
    groups: localStorage.getItem('user_groups')
      ? JSON.parse(localStorage.getItem('user_groups') as string)
      : [],
    permissions: localStorage.getItem('user_permissions')
      ? JSON.parse(localStorage.getItem('user_permissions') as string)
      : [],
    menus: localStorage.getItem('user_menus')
      ? JSON.parse(localStorage.getItem('user_menus') as string)
      : [],
    currentGroupId: localStorage.getItem('current_group_id')
      ? parseInt(localStorage.getItem('current_group_id') as string)
      : null,
  }),

  getters: {
    isLogin: (state) => !!state.token,

    isAdmin: (state): boolean => {
      return state.roles.some((r) => r.role_code === 'admin')
    },

    isPlatformAdmin: (state): boolean => {
      return state.roles.some(
        (r) => r.role_code === 'admin' && r.scope_type === 'platform',
      )
    },

    isGovernor: (state): boolean => {
      return state.roles.some((r) => r.role_code === 'governor')
    },

    displayName: (state): string => {
      return state.userInfo?.real_name || state.userInfo?.username || '当前用户'
    },

    agencyName: (state): string => {
      return state.userInfo?.agency_name || ''
    },

    activeGroups: (state): GroupInfoItem[] => {
      return state.groups.filter((g) => g.status === 'active')
    },

    currentGroupName: (state): string => {
      if (!state.currentGroupId) return ''
      const group = state.groups.find((g) => g.group_id === state.currentGroupId)
      return group?.group_name || ''
    },

    hasPermission: (state) => {
      return (permission: string): boolean => {
        return state.permissions.includes(permission)
      }
    },

    hasRole: (state) => {
      return (roleCode: string, scopeType?: string): boolean => {
        return state.roles.some(
          (r) =>
            r.role_code === roleCode &&
            (scopeType === undefined || r.scope_type === scopeType),
        )
      }
    },

    // 是否有菜单路径的访问权限
    hasMenuPath: (state) => {
      return (path: string): boolean => {
        return state.menus.some((m) => m.path === path)
      }
    },
  },

  actions: {
    async login(params: LoginParams) {
      const res: any = await loginApi(params)
      const data = res.data || {}

      const token = data.access_token || data.token

      if (!token) {
        throw new Error('登录接口未返回 access_token')
      }

      this.token = token
      this.tokenType = data.token_type || 'bearer'
      this.userInfo = data.user || null

      localStorage.setItem('access_token', this.token)
      localStorage.setItem('token_type', this.tokenType)

      if (this.userInfo) {
        localStorage.setItem('user_info', JSON.stringify(this.userInfo))
      }

      // 登录后获取完整用户信息
      await this.fetchCurrentUser()

      return data
    },

    async fetchCurrentUser() {
      const res: any = await getMeApi()
      const data = res.data || {}

      this.userInfo = {
        id: data.id,
        username: data.username,
        real_name: data.real_name,
        agency_id: data.agency_id,
        agency_name: data.agency_name,
        current_group_id: data.current_group_id,
      }
      this.roles = data.roles || []
      this.groups = data.groups || []
      this.permissions = data.permissions || []

      // 默认群组
      if (data.current_group_id) {
        this.currentGroupId = data.current_group_id
      } else if (this.activeGroups.length > 0) {
        this.currentGroupId = this.activeGroups[0].group_id
      }

      this._persistState()

      // 同时获取菜单
      await this.fetchMenus()

      return data
    },

    async fetchMenus() {
      const res: any = await getMenusApi()
      this.menus = res.data || []
      localStorage.setItem('user_menus', JSON.stringify(this.menus))
      return this.menus
    },

    async logout() {
      try {
        await logoutApi()
      } catch (error) {
        // 后端 logout 即使失败，前端也清理本地状态
      }

      this.clearAuth()
    },

    clearAuth() {
      this.token = ''
      this.tokenType = 'bearer'
      this.userInfo = null
      this.roles = []
      this.groups = []
      this.permissions = []
      this.menus = []
      this.currentGroupId = null

      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      localStorage.removeItem('user_info')
      localStorage.removeItem('user_roles')
      localStorage.removeItem('user_groups')
      localStorage.removeItem('user_permissions')
      localStorage.removeItem('user_menus')
      localStorage.removeItem('current_group_id')
    },

    setCurrentGroupId(groupId: number | null) {
      this.currentGroupId = groupId
      localStorage.setItem(
        'current_group_id',
        groupId ? String(groupId) : '',
      )
    },

    _persistState() {
      localStorage.setItem('user_info', JSON.stringify(this.userInfo))
      localStorage.setItem('user_roles', JSON.stringify(this.roles))
      localStorage.setItem('user_groups', JSON.stringify(this.groups))
      localStorage.setItem('user_permissions', JSON.stringify(this.permissions))
      localStorage.setItem(
        'current_group_id',
        this.currentGroupId ? String(this.currentGroupId) : '',
      )
    },
  },
})
