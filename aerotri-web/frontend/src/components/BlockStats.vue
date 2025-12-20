<template>
  <div class="block-stats">
    <el-descriptions :column="2" border size="small">
      <el-descriptions-item label="状态">
        <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="算法">
        {{ block.algorithm === 'glomap' ? 'GLOMAP' : block.algorithm === 'instantsfm' ? 'InstantSfM' : 'COLMAP' }}
      </el-descriptions-item>
      <el-descriptions-item label="注册图像">
        {{ block.statistics?.num_registered_images || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="3D 点数">
        {{ formatNumber(block.statistics?.num_points3d) }}
      </el-descriptions-item>
      <el-descriptions-item label="观测数">
        {{ formatNumber(block.statistics?.num_observations) }}
      </el-descriptions-item>
      <el-descriptions-item label="平均轨迹长度">
        {{ block.statistics?.mean_track_length?.toFixed(2) || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="重投影误差">
        {{ block.statistics?.mean_reprojection_error?.toFixed(4) || '-' }} px
      </el-descriptions-item>
      <el-descriptions-item label="总耗时">
        {{ formatTime(block.statistics?.total_time) }}
      </el-descriptions-item>
    </el-descriptions>

    <!-- Stage Times -->
    <div class="stage-times" v-if="block.statistics?.stage_times">
      <h4>各阶段耗时</h4>
      <div class="time-list">
        <div 
          v-for="(time, stage) in block.statistics.stage_times" 
          :key="stage"
          class="time-item"
        >
          <span class="stage-name">{{ stageLabels[stage] || stage }}</span>
          <span class="stage-time">{{ formatTime(time) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Block } from '@/types'

const props = defineProps<{
  block: Block
}>()

const stageLabels: Record<string, string> = {
  feature_extraction: '特征提取',
  matching: '特征匹配',
  mapping: '重建',
}

const statusType = computed(() => {
  switch (props.block.status) {
    case 'completed': return 'success'
    case 'running': return ''
    case 'failed': return 'danger'
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
</script>

<style scoped>
.block-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-times h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #606266;
}

.time-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.time-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.stage-name {
  color: #606266;
}

.stage-time {
  color: #909399;
}
</style>
