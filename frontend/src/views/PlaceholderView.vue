<template>
  <div class="placeholder-page">
    <el-card shadow="never" class="placeholder-card">
      <el-empty :description="`${pageTitle}页面待完善`">
        <el-button type="primary" @click="$router.push('/dashboard')">
          返回首页总览
        </el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitle = computed(() => {
  return String(route.meta.title || '当前')
})
</script>

<style scoped>
.placeholder-page {
  padding: 24px;
}

.placeholder-card {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>