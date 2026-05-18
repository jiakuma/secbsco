// Axios 请求封装
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
})

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 可选：携带当前群组 ID
    const currentGroupId = localStorage.getItem('current_group_id')
    if (currentGroupId) {
      config.headers['X-Group-Id'] = currentGroupId
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

request.interceptors.response.use(
  (response) => {
    const res = response.data

    if (res && typeof res.code !== 'undefined' && res.code !== 0) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(res)
    }

    return res
  },
  (error: AxiosError<any>) => {
    const status = error.response?.status

    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('token_type')
      localStorage.removeItem('user_info')
      localStorage.removeItem('user_roles')
      localStorage.removeItem('user_groups')
      localStorage.removeItem('user_permissions')
      localStorage.removeItem('user_menus')
      localStorage.removeItem('current_group_id')

      ElMessage.error('登录已失效，请重新登录')
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error('无权限访问该资源')
    } else if (status === 404) {
      ElMessage.error('资源不存在或无权访问')
    } else {
      ElMessage.error(error.response?.data?.message || '网络请求异常')
    }

    return Promise.reject(error)
  },
)

export default request
