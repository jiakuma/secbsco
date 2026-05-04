// 登录认证相关接口
import request from './request'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginData {
  access_token?: string
  token?: string
  token_type?: string
  user?: any
}

export function loginApi(data: LoginParams) {
  return request.post<{
    code: number
    message: string
    data: LoginData
  }>('/api/auth/login', data)
}

export function getMeApi() {
  return request.get('/api/auth/me')
}

export function logoutApi() {
  return request.post('/api/auth/logout')
}
