<template>
  <el-card 
    class="block-card" 
    :class="{ 'is-running': block.status === 'running' }"
    shadow="hover"
  >
    <template #header>
      <div class="card-header">
        <span class="block-name">{{ block.name }}</span>
        <el-dropdown @command="handleCommand" trigger="click">
          <el-button type="text" :icon="MoreFilled" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-if="canReset"
                command="reset"
              >
                <el-icon><RefreshRight /></el-icon>
                重置
              </el-dropdown-item>
              <el-dropdown-item command="delete" :disabled="block.status === 'running'">
                <el-icon><Delete /></el-icon>
                删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </template>
    
    <div class="card-content" @click="$emit('click')">
      <!-- Status Badge -->
      <div class="status-row">
        <el-tag :type="statusType" size="small">
          {{ statusText }}
        </el-tag>
        <el-tag type="info" size="small">
          {{ algorithmText }}
        </el-tag>
        <el-tag type="info" size="small" effect="plain">
          {{ imageCountText }}
        </el-tag>
      </div>
      
      <!-- Progress (if running) -->
      <div v-if="block.status === 'running'" class="progress-section">
        <div class="stage-text">{{ block.current_stage || '准备中' }}</div>
        <el-progress 
          :percentage="block.progress || 0" 
          :stroke-width="8"
          :show-text="true"
        />
      </div>
      
      <!-- Statistics (if completed) -->
      <div v-else-if="block.status === 'completed' && block.statistics" class="stats-section">
        <div class="stat-item">
          <span class="stat-label">注册图像</span>
          <span class="stat-value">{{ block.statistics.num_registered_images || '-' }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">3D点数</span>
          <span class="stat-value">{{ formatNumber(block.statistics.num_points3d) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">耗时</span>
          <span class="stat-value">{{ formatTime(block.statistics.total_time) }}</span>
        </div>
      </div>
      
      <!-- Error (if failed) -->
      <div v-else-if="block.status === 'failed'" class="error-section">
        <el-text type="danger" truncated>
          {{ block.error_message || '处理失败' }}
        </el-text>
      </div>
      
      <!-- Path -->
      <div class="path-section">
        <el-icon><Folder /></el-icon>
        <el-text class="path-text" truncated>
          {{ block.image_path }}
        </el-text>
      </div>
      
      <!-- Time -->
      <div class="time-section">
        <el-text type="info" size="small">
          创建于 {{ formatDate(block.created_at) }}
        </el-text>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MoreFilled, Delete, Folder, RefreshRight } from '@element-plus/icons-vue'
import type { Block } from '@/types'

const props = defineProps<{
  block: Block
}>()

const emit = defineEmits<{
  (e: 'click'): void
  (e: 'delete', block: Block): void
  (e: 'reset', block: Block): void
}>()

const statusType = computed(() => {
  switch (props.block.status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    case 'cancelled': return 'warning'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (props.block.status) {
    case 'created': return '待处理'
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return props.block.status
  }
})

const algorithmText = computed(() => {
  if (props.block.algorithm === 'glomap') return 'GLOMAP'
  if (props.block.algorithm === 'instantsfm') return 'InstantSfM'
  if (props.block.algorithm === 'openmvg_global') return 'OpenMVG'
  return 'COLMAP'
})

const imageCountText = computed(() => {
  const n = props.block.statistics?.num_images
  return `图像 ${typeof n === 'number' ? n : '-'}`
})

const canReset = computed(() => {
  // Only show reset for failed, completed, or cancelled blocks
  return ['failed', 'completed', 'cancelled'].includes(props.block.status)
})

function handleCommand(command: string) {
  if (command === 'delete') {
    emit('delete', props.block)
  } else if (command === 'reset') {
    emit('reset', props.block)
  }
}

function formatNumber(num: number | undefined): string {
  if (num === undefined) return '-'
  return num.toLocaleString()
}

function formatTime(seconds: number | undefined): string {
  if (seconds === undefined) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.block-card {
  cursor: pointer;
  transition: all 0.3s;
}

.block-card.is-running {
  border-color: var(--el-color-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.block-name {
  font-weight: 600;
  font-size: 16px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-row {
  display: flex;
  gap: 8px;
}

.progress-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-text {
  font-size: 13px;
  color: var(--el-color-primary);
}

.stats-section {
  display: flex;
  justify-content: space-between;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.error-section {
  padding: 8px 0;
}

.path-section {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.path-text {
  flex: 1;
  font-size: 13px;
}

.time-section {
  font-size: 12px;
}
</style>
