<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-title">
        <div class="logo">联</div>
        <div>
          <h1>生物安全数据联合统计系统</h1>
          <p>Biosecurity Federated Statistics Platform</p>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="handleLogin"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            placeholder="请输入密码"
            size="large"
            show-password
            clearable
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="login-button"
          :loading="loading"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <div class="login-footer">
        多机构联合统计 · 隐私计算 · 可信存证
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true

    try {
      await authStore.login({
        username: form.username,
        password: form.password,
      })

      ElMessage.success('登录成功')
      router.push('/dashboard')
    } catch (error: any) {
      ElMessage.error(error?.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 20% 20%, rgba(64, 158, 255, 0.18), transparent 30%),
    radial-gradient(circle at 80% 10%, rgba(103, 194, 58, 0.12), transparent 28%),
    linear-gradient(135deg, #eef4ff 0%, #f8fbff 45%, #ffffff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 420px;
  padding: 36px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 20px 60px rgba(31, 45, 61, 0.12);
  border: 1px solid rgba(220, 230, 245, 0.9);
}

.login-title {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 32px;
}

.logo {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
}

.login-title h1 {
  font-size: 22px;
  line-height: 1.3;
  color: #1f2937;
  margin: 0;
}

.login-title p {
  font-size: 13px;
  color: #7b8794;
  margin: 6px 0 0;
}

.login-button {
  width: 100%;
  margin-top: 8px;
}

.login-footer {
  margin-top: 24px;
  text-align: center;
  color: #8a96a8;
  font-size: 13px;
}
</style>