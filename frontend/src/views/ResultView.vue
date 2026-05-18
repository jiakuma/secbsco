<template>
  <div class="placeholder-page">
    <div class="placeholder-content">
      <div class="placeholder-icon">📊</div>
      <h2>结果展示</h2>
      <p class="desc">查看联合统计与联邦学习任务的计算结果。</p>
      <p class="hint">该功能将在后续阶段完善。</p>
      <el-button type="primary" @click="router.push('/tasks')">查看任务列表</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.placeholder-page {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder-content { text-align: center; }
.placeholder-icon { font-size: 64px; margin-bottom: 16px; }
h2 { font-size: 24px; color: #111827; margin-bottom: 8px; }
.desc { font-size: 15px; color: #4b5563; margin-bottom: 8px; }
.hint { font-size: 13px; color: #9ca3af; margin-bottom: 24px; }
</style>
