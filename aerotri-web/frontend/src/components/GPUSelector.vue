<template>
  <div class="gpu-selector">
    <div v-if="loading" class="loading">
      <el-skeleton :rows="2" animated />
    </div>

    <div v-else-if="gpus.length === 0" class="no-gpu">
      <el-text type="info">未检测到 GPU</el-text>
    </div>

    <div v-else class="gpu-list">
      <div
        v-for="gpu in gpus"
        :key="gpu.index"
        class="gpu-item"
        :class="{ 
          'is-selected': gpu.index === modelValue,
          'is-unavailable': !gpu.is_available
        }"
        @click="selectGPU(gpu)"
      >
        <div class="gpu-header">
          <el-radio :model-value="modelValue" :value="gpu.index" :disabled="!gpu.is_available">
            GPU {{ gpu.index }}: {{ gpu.name }}
          </el-radio>
        </div>
        <div class="gpu-stats">
          <div class="stat">
            <span class="label">显存</span>
            <el-progress
              :percentage="memoryPercentage(gpu)"
              :stroke-width="6"
              :show-text="false"
              :status="memoryStatus(gpu)"
            />
            <span class="value">{{ gpu.memory_used }} / {{ gpu.memory_total }} MB</span>
          </div>
          <div class="stat">
            <span class="label">利用率</span>
            <el-progress
              :percentage="gpu.utilization"
              :stroke-width="6"
              :show-text="false"
              :status="utilizationStatus(gpu)"
            />
            <span class="value">{{ gpu.utilization }}%</span>
          </div>
        </div>
        <el-tag 
          v-if="!gpu.is_available" 
          type="warning" 
          size="small"
          class="unavailable-tag"
        >
          繁忙
        </el-tag>
      </div>
    </div>

    <el-button
      v-if="!autoRefreshActive"
      text
      type="primary"
      @click="refresh"
      :loading="loading"
      class="refresh-btn"
    >
      <el-icon><Refresh /></el-icon>
      刷新
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useGPUStore } from '@/stores/gpu'
import { storeToRefs } from 'pinia'
import type { GPUInfo } from '@/types'

const props = defineProps<{
  modelValue: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const gpuStore = useGPUStore()
const { gpus, loading } = storeToRefs(gpuStore)
const autoRefreshActive = ref(false)

onMounted(() => {
  gpuStore.fetchGPUs()
  startAutoRefresh()
})

const AUTO_REFRESH_INTERVAL = 2000
let refreshTimer: ReturnType<typeof setInterval> | null = null

function startAutoRefresh() {
  refreshTimer = setInterval(() => {
    gpuStore.fetchGPUs({ showLoading: false })
  }, AUTO_REFRESH_INTERVAL)
  autoRefreshActive.value = true
}

onBeforeUnmount(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
    autoRefreshActive.value = false
  }
})

function selectGPU(gpu: GPUInfo) {
  if (gpu.is_available) {
    emit('update:modelValue', gpu.index)
  }
}

function refresh() {
  gpuStore.fetchGPUs()
}

function memoryPercentage(gpu: GPUInfo): number {
  return Math.round((gpu.memory_used / gpu.memory_total) * 100)
}

function memoryStatus(gpu: GPUInfo): '' | 'success' | 'warning' | 'exception' {
  const pct = memoryPercentage(gpu)
  if (pct > 90) return 'exception'
  if (pct > 70) return 'warning'
  return 'success'
}

function utilizationStatus(gpu: GPUInfo): '' | 'success' | 'warning' | 'exception' {
  if (gpu.utilization > 90) return 'exception'
  if (gpu.utilization > 70) return 'warning'
  return 'success'
}
</script>

<style scoped>
.gpu-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gpu-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gpu-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.gpu-item:hover {
  border-color: var(--el-color-primary-light-3);
}

.gpu-item.is-selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.gpu-item.is-unavailable {
  opacity: 0.6;
  cursor: not-allowed;
}

.gpu-header {
  margin-bottom: 8px;
}

.gpu-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-left: 24px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.stat .label {
  width: 40px;
  color: #909399;
}

.stat .el-progress {
  flex: 1;
}

.stat .value {
  width: 100px;
  text-align: right;
  color: #606266;
}

.unavailable-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.refresh-btn {
  align-self: flex-start;
}
</style>
