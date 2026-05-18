<template>
  <div class="forbidden-page">
    <div class="forbidden-content">
      <div class="forbidden-icon">🔒</div>
      <h1>403 - 无权限</h1>
      <p>您没有权限访问该页面</p>
      <el-button type="primary" @click="router.push('/dashboard')">
        返回首页
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.forbidden-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fb;
}
.forbidden-content {
  text-align: center;
}
.forbidden-icon {
  font-size: 64px;
  margin-bottom: 16px;
}
h1 {
  font-size: 28px;
  color: #111827;
  margin-bottom: 8px;
}
p {
  font-size: 16px;
  color: #6b7280;
  margin-bottom: 24px;
}
</style>
