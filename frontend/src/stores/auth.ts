// Pinia 登录状态管理
import { defineStore } from 'pinia'
import { loginApi, getMeApi, logoutApi, type LoginParams } from '@/api/auth'

interface AuthState {
  token: string
  tokenType: string
  userInfo: any | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('access_token') || '',
    tokenType: localStorage.getItem('token_type') || 'bearer',
    userInfo: localStorage.getItem('user_info')
      ? JSON.parse(localStorage.getItem('user_info') as string)
      : null,
  }),

  getters: {
    isLogin: (state) => !!state.token,
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

      return data
    },

    async fetchMe() {
      const res: any = await getMeApi()
      this.userInfo = res.data

      localStorage.setItem('user_info', JSON.stringify(this.userInfo))

      return res.data
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

      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      localStorage.removeItem('user_info')
    },
  },
})