<template>
  <div class="fl-module-wrapper">
    <div class="module-title">
      <div class="title-indicator"></div>
      <h3>联邦学习训练过程</h3>
    </div>

    <div class="fl-main-card">

      <header class="fl-header">
        <div class="epoch-badge">
          <div class="epoch-icon-box">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <span class="epoch-text">Epoch <span class="epoch-num">{{ currentRound }}</span> / {{ totalRounds }}</span>
        </div>
        <div class="stage-info">
          <span class="label">当前阶段：</span>
          <span class="value">{{ trainingSteps[currentStep].name }}</span>
        </div>
      </header>

      <nav class="fl-stepper">
        <div
          v-for="(step, index) in trainingSteps"
          :key="index"
          class="step-item"
          :class="{
            active: currentStep === index,
            completed: currentStep > index
          }"
        >
          <div class="step-node">
            <el-icon v-if="currentStep > index"><Select /></el-icon>
            <span v-else>{{ index + 1 }}</span>
          </div>
          <span class="step-label">{{ step.name }}</span>
          <div
            v-if="index < trainingSteps.length - 1"
            class="step-line"
            :class="{
              'line-completed': currentStep > index,
              'line-active': currentStep === index
            }"
          ></div>
        </div>
      </nav>

      <main class="fl-canvas">
        <div class="canvas-inner" :style="{ width: canvasWidth + 'px' }">

          <div class="node-wrapper master-wrapper">
            <div class="fl-card master-card">
              <div class="icon-box master-icon">
                <el-icon :class="{ 'is-spinning': currentStep === 3 }"><Box /></el-icon>
              </div>
              <div class="info-box">
                <h4>SecretFlow 主节点</h4>
                <p class="meta"><el-icon><RefreshRight /></el-icon> 聚合轮次：{{ currentRound }} / {{ totalRounds }}</p>
                <p class="meta status-text"><el-icon><Clock /></el-icon> 状态：{{ trainingSteps[currentStep].statusDesc }}</p>
              </div>
            </div>
          </div>

          <div class="connection-layer">
            <svg class="lines-svg" :viewBox="`0 0 ${canvasWidth} 170`" preserveAspectRatio="none">
              <defs>
                <marker id="arrowUpload" markerWidth="16" markerHeight="16" refX="4" refY="8" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M2,2 L12,8 L2,14 Z" fill="#3B82F6" />
                </marker>
                <marker id="arrowDownload" markerWidth="16" markerHeight="16" refX="2" refY="8" orient="auto-start-reverse" markerUnits="userSpaceOnUse">
                  <path d="M2,2 L12,8 L2,14 Z" fill="#3B82F6" />
                </marker>
              </defs>

              <g v-for="(party, index) in localParties" :key="'link-'+index">
                <path :d="getPath(index)" class="base-path" />

                <template v-if="isTransmitting">
                  <path
                    :d="getPath(index)"
                    class="flow-path"
                    :class="{ 'reverse-flow': currentStep === 4 }"
                    :marker-end="currentStep === 2 ? 'url(#arrowUpload)' : ''"
                    :marker-start="currentStep === 4 ? 'url(#arrowDownload)' : ''"
                  />
                  <circle r="4.5" fill="#0EA5E9" stroke="#FFFFFF" stroke-width="1.5" class="flow-dot">
                    <animateMotion
                      :path="getPath(index)"
                      dur="1.5s"
                      repeatCount="indefinite"
                      :keyPoints="currentStep === 4 ? '1;0' : '0;1'"
                      keyTimes="0;1"
                      calcMode="linear"
                    />
                  </circle>
                </template>
              </g>
            </svg>
          </div>

          <div class="clients-row">
            <div
              v-for="(party, index) in localParties"
              :key="party.node_id || index"
              class="client-wrapper"
            >
              <div class="fl-card client-card" :class="{ 'is-computing': currentStep === 1 }">
                <div class="icon-box client-icon">
                  <el-icon><Monitor /></el-icon>
                </div>
                <div class="info-box">
                  <h4>{{ party.node_name || `Node_${party.node_id}` }}</h4>
                  <p class="meta meta-light">算力：{{ party.power || '未知' }}</p>

                  <div class="status-pill" :class="getStatusClass(party.status || 'idle')">
                    <el-icon v-if="party.status === 'uploading'"><Lock /></el-icon>
                    <el-icon v-else-if="party.status === 'completed'"><Check /></el-icon>
                    <el-icon v-else><Loading v-if="party.status === 'training'" /><Cpu v-else /></el-icon>
                    <span>{{ getStatusText(party.status || 'idle') }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>

      <footer class="fl-controls">
        <el-button type="primary" class="action-btn" :icon="isPlaying ? VideoPause : VideoPlay" @click="toggle">
          {{ isPlaying ? '暂停训练' : '开始演示' }}
        </el-button>
        <el-button class="action-btn plain-btn" icon="Refresh" @click="reset">重置拓扑</el-button>
      </footer>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  Select, TrendCharts, Box, Monitor, Lock, Cpu,
  VideoPlay, VideoPause, Refresh, Clock, RefreshRight, Loading, Check
} from '@element-plus/icons-vue'

// ================= 定义 Props =================
interface PartyNode {
  node_id: string | number;
  node_name?: string;
  power?: string | number;
  status?: 'idle' | 'training' | 'uploading' | 'completed';
  [key: string]: any;
}

const props = defineProps({
  parties: {
    type: Array as () => PartyNode[],
    default: () => [
      { node_id: 4, power: 8, status: 'idle' },
      { node_id: 3, power: 7, status: 'idle' },
      { node_id: 2, power: 6, status: 'idle' }
    ]
  },
  totalRounds: { type: Number, default: 5 }
})

// ================= 状态管理 =================
const localParties = ref<PartyNode[]>([])
const currentRound = ref(1)
const currentStep = ref(0)
const isPlaying = ref(false)
let timer: any = null

// 监听外部传入的节点，同步到本地动画驱动状态
watch(() => props.parties, (newVal) => {
  localParties.value = JSON.parse(JSON.stringify(newVal))
}, { immediate: true, deep: true })

const trainingSteps = [
  { name: '网络初始化', statusDesc: '等待各节点接入网络...' },
  { name: '本地加密训练', statusDesc: '各节点执行本地计算中' },
  { name: '梯度安全上传', statusDesc: '等待各节点梯度上传' },
  { name: 'Sparse 聚合', statusDesc: '正在进行多方安全聚合计算' },
  { name: '全局模型下发', statusDesc: '分发最新全局参数至各节点' }
]

const isTransmitting = computed(() => currentStep.value === 2 || currentStep.value === 4)

// ================= 核心算法：动态计算画布与路径 =================

// 1. 动态画布宽度：最少 860px，如果节点过多(如 4+ 个)，每个额外占用 260px 横向空间
const canvasWidth = computed(() => {
  const n = localParties.value.length;
  return Math.max(860, n * 260);
})

// 2. 动态 SVG 路径生成 (完美对齐 flex space-between)
const getPath = (index: number) => {
  const n = localParties.value.length;
  const W = canvasWidth.value;
  const masterX = W / 2; // 主节点永远在正中心

  // 计算客户端 X 轴中心点 (startX)
  let startX = masterX;
  if (n > 1) {
    const gap = (W - n * 220) / (n - 1);
    startX = 110 + index * (220 + gap); // 110 是半个卡片宽度
  }

  // 计算主节点接入点 (endX)，确保多条线在主节点下方不重叠
  let endX = masterX;
  if (n > 1) {
    const maxSpread = 240;
    const spread = Math.min(maxSpread, (n - 1) * 80);
    endX = masterX - spread / 2 + (spread / (n - 1)) * index;
  }

  // 如果点位都在中间，画直线
  if (Math.abs(startX - endX) < 5) {
    return `M${startX},140 L${endX},45`;
  }
  // 否则画平滑贝塞尔曲线，Y=45 防止箭头戳进主卡片
  return `M${startX},140 C${startX},80 ${endX},90 ${endX},45`;
}

// ================= 动画生命周期 =================
const toggle = () => {
  isPlaying.value = !isPlaying.value
  if (isPlaying.value) run()
  else clearTimeout(timer)
}

const run = () => {
  if (!isPlaying.value) return
  updateStatuses()

  timer = setTimeout(() => {
    if (currentStep.value < 4) {
      currentStep.value++
    } else {
      currentStep.value = 0
      currentRound.value++
    }

    if (currentRound.value > props.totalRounds) {
      isPlaying.value = false
      currentRound.value = props.totalRounds
      return
    }
    run()
  }, getStepDuration())
}

const getStepDuration = () => [1000, 2500, 2000, 1500, 2000][currentStep.value]

const updateStatuses = () => {
  const step = currentStep.value
  localParties.value.forEach(p => {
    if (step === 1) p.status = 'training'
    else if (step === 2) p.status = 'uploading'
    else if (step === 4) p.status = 'completed'
    else p.status = 'idle'
  })
}

const reset = () => {
  clearTimeout(timer)
  isPlaying.value = false
  currentStep.value = 0
  currentRound.value = 1
  localParties.value.forEach(p => p.status = 'idle')
}

// 文本与样式解析
const getStatusText = (status: string) => {
  const map: Record<string, string> = { idle: '节点待命', training: '模型训练中', uploading: '梯度上传中', completed: '模型已同步' }
  return map[status] || '未知'
}

const getStatusClass = (status: string) => {
  const map: Record<string, string> = { idle: 'tag-default', training: 'tag-warning', uploading: 'tag-primary', completed: 'tag-success' }
  return map[status] || 'tag-default'
}

onMounted(() => setTimeout(toggle, 500))
onUnmounted(() => clearTimeout(timer))
</script>

<style scoped>
.fl-module-wrapper {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #333;
  padding: 20px;
}

.module-title {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}
.title-indicator {
  width: 4px;
  height: 18px;
  background-color: #3B82F6;
  border-radius: 2px;
  margin-right: 10px;
}
.module-title h3 { margin: 0; font-size: 16px; font-weight: 600; color: #1E293B; }

.fl-main-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  padding: 32px 40px;
}

/* Header */
.fl-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}
.epoch-badge { display: flex; align-items: center; gap: 12px; }
.epoch-icon-box {
  width: 36px;
  height: 36px;
  background: #3B82F6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FFF;
  font-size: 20px;
}
.epoch-text { font-size: 20px; color: #64748B; font-weight: 500; }
.epoch-num { color: #2563EB; font-size: 24px; font-weight: 700; }
.stage-info { display: flex; align-items: center; margin-left: 20px; padding-left: 20px; border-left: 1px solid #E2E8F0; }
.stage-info .label { color: #64748B; font-size: 15px; }
.stage-info .value { color: #2563EB; font-weight: 600; font-size: 16px; }

/* Stepper */
.fl-stepper { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; padding: 0 40px; }
.step-item { display: flex; flex-direction: column; align-items: center; position: relative; flex: 1; }
.step-node {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #F1F5F9;
  border: 2px solid #CBD5E1;
  color: #94A3B8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  z-index: 2;
  transition: all 0.3s;
}
.step-label { margin-top: 10px; font-size: 13px; color: #94A3B8; }
.step-line { position: absolute; top: 14px; left: calc(50% + 20px); width: calc(100% - 40px); height: 2px; background: #E2E8F0; z-index: 1; transition: background 0.3s; }
.step-item.active .step-node { background: #3B82F6; border-color: #3B82F6; color: #FFF; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15); }
.step-item.active .step-label { color: #2563EB; font-weight: 600; }
.step-item.completed .step-node { background: #FFF; border-color: #22C55E; color: #22C55E; }
.step-item.completed .step-label { color: #22C55E; }
.line-completed { background: #22C55E; }
.line-active { background: linear-gradient(90deg, #22C55E 0%, #3B82F6 100%); }

/* 画布基础系 (新增横向滚动容器支持大量节点) */
.fl-canvas {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 20px 0;
}
.fl-canvas::-webkit-scrollbar { height: 6px; }
.fl-canvas::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }

.canvas-inner {
  margin: 0 auto;
  position: relative;
}

/* 卡片通用 */
.fl-card {
  background: #FFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  padding: 16px 20px;
  gap: 16px;
  transition: all 0.3s;
}
.icon-box {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
}
.info-box h4 { margin: 0 0 6px 0; font-size: 15px; color: #1E293B; }
.info-box .meta { margin: 0; font-size: 12px; color: #64748B; display: flex; align-items: center; gap: 4px; line-height: 1.6;}

/* 主节点 */
.master-wrapper {
  width: 320px;
  margin: 0 auto;
}
.master-card {
  border: 1px solid #BFDBFE;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.08);
}
.master-icon { background: #EFF6FF; color: #3B82F6; font-size: 30px;}
.master-card .status-text { color: #2563EB; font-weight: 500; margin-top: 2px;}
.is-spinning { animation: pulse 2s infinite; }

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

/* 连线层 */
.connection-layer {
  position: relative;
  width: 100%;
  height: 170px;
  pointer-events: none;
}
.lines-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.base-path {
  fill: none;
  stroke: #CBD5E1;
  stroke-width: 2;
  stroke-dasharray: 6 6;
}
.flow-path {
  fill: none;
  stroke: #3B82F6;
  stroke-width: 2.5;
  stroke-dasharray: 6 6;
  animation: flowDash 0.8s linear infinite;
}
.reverse-flow { animation-direction: reverse; }

@keyframes flowDash {
  to { stroke-dashoffset: -12; }
}
.flow-dot {
  filter: drop-shadow(0 0 4px rgba(14, 165, 233, 0.4));
}

/* 边缘节点群 */
.clients-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.client-wrapper { width: 220px; }
.client-card { width: 100%; box-sizing: border-box; padding: 16px 14px; }
.client-icon { background: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; width: 44px; height: 44px; font-size: 22px; }
.meta-light { color: #94A3B8 !important; }

/* 正在计算高亮 */
.is-computing { border-color: #FCD34D; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.1); }
.is-computing .client-icon { color: #D97706; background: #FEF3C7; border-color: #FDE68A; }

/* 状态药丸 */
.status-pill {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 500;
}
.tag-default { background: #F1F5F9; color: #64748B; }
.tag-warning { background: #FEF3C7; color: #D97706; }
.tag-primary { background: #EFF6FF; color: #2563EB; }
.tag-success { background: #DCFCE7; color: #16A34A; }

/* 底部操作 */
.fl-controls { display: flex; justify-content: center; gap: 16px; margin-top: 40px; padding-top: 24px; border-top: 1px solid #F1F5F9; }
.action-btn { padding: 10px 24px; border-radius: 8px; font-weight: 500; }
.plain-btn { background: #FFF; border: 1px solid #CBD5E1; color: #475569; }
.plain-btn:hover { background: #F8FAFC; color: #1E293B; border-color: #94A3B8; }
</style>