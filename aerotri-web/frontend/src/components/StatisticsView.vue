<template>
  <div class="statistics-view">
    <!-- Summary Cards -->
    <div class="summary-cards">
      <el-card class="summary-card">
        <div class="summary-content">
          <div class="summary-value">{{ stats.num_registered_images || '-' }}</div>
          <div class="summary-label">注册图像数</div>
        </div>
        <el-icon class="summary-icon" :size="40"><Camera /></el-icon>
      </el-card>

      <el-card class="summary-card">
        <div class="summary-content">
          <div class="summary-value">{{ formatNumber(stats.num_points3d) }}</div>
          <div class="summary-label">3D 点数</div>
        </div>
        <el-icon class="summary-icon" :size="40"><Location /></el-icon>
      </el-card>

      <el-card class="summary-card">
        <div class="summary-content">
          <div class="summary-value">{{ formatNumber(stats.num_observations) }}</div>
          <div class="summary-label">观测数</div>
        </div>
        <el-icon class="summary-icon" :size="40"><View /></el-icon>
      </el-card>

      <el-card class="summary-card">
        <div class="summary-content">
          <div class="summary-value">{{ formatTime(totalTime) }}</div>
          <div class="summary-label">总耗时</div>
        </div>
        <el-icon class="summary-icon" :size="40"><Timer /></el-icon>
      </el-card>
    </div>

    <!-- Detailed Stats -->
    <el-row :gutter="20">
      <!-- Reconstruction Quality -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>重建质量</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="平均重投影误差">
              {{ stats.mean_reprojection_error?.toFixed(4) || '-' }} px
            </el-descriptions-item>
            <el-descriptions-item label="平均轨迹长度">
              {{ stats.mean_track_length?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="注册成功率">
              {{ successRate }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- Stage Times -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>各阶段耗时</span>
          </template>
          <div class="stage-times">
            <div v-for="(time, stage) in stageTimes" :key="stage" class="stage-time-item">
              <div class="stage-info">
                <span class="stage-name">{{ stageLabels[stage] || stage }}</span>
                <span class="stage-value">{{ formatTime(time) }}</span>
              </div>
              <el-progress
                :percentage="(time / totalTime) * 100"
                :stroke-width="8"
                :show-text="false"
              />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Algorithm Parameters -->
    <el-card class="params-card">
      <template #header>
        <span>算法参数</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="算法">
          {{ block.algorithm === 'glomap' ? 'GLOMAP' : 'COLMAP' }}
        </el-descriptions-item>
        <el-descriptions-item label="匹配方法">
          {{ matchingMethodLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="GPU Index">
          {{ algorithmParams.gpu_index ?? 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="最大图像尺寸">
          {{ block.feature_params?.max_image_size || 2000 }}
        </el-descriptions-item>
        <el-descriptions-item label="最大特征数">
          {{ block.feature_params?.max_num_features || 4096 }}
        </el-descriptions-item>
        <el-descriptions-item label="相机模型">
          {{ block.feature_params?.camera_model || 'SIMPLE_RADIAL' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Camera, Location, View, Timer } from '@element-plus/icons-vue'
import type { Block, BlockStatistics } from '@/types'
import { resultApi } from '@/api'

const props = defineProps<{
  block: Block
}>()

const stageLabels: Record<string, string> = {
  feature_extraction: '特征提取',
  matching: '特征匹配',
  mapping: '重建',
  preprocessing: '预处理',
  relative_pose_estimation: '相对位姿估计',
  rotation_averaging: '旋转平均',
  track_establishment: '轨迹建立',
  global_positioning: '全局定位',
  bundle_adjustment: '光束法平差',
  retriangulation: '重三角化',
}

const stats = ref<BlockStatistics>({})

const stageTimes = computed(() => {
  return props.block.statistics?.stage_times || {}
})

const totalTime = computed(() => {
  return props.block.statistics?.total_time || 
    Object.values(stageTimes.value).reduce((a, b) => a + b, 0)
})

const algorithmParams = computed(() => {
  return props.block.statistics?.algorithm_params || {}
})

const successRate = computed(() => {
  const registered = stats.value.num_registered_images || 0
  const total = stats.value.num_images || registered
  if (total === 0) return '-'
  return `${((registered / total) * 100).toFixed(1)}%`
})

const matchingMethodLabel = computed(() => {
  switch (props.block.matching_method) {
    case 'sequential': return '序列匹配'
    case 'exhaustive': return '穷举匹配'
    case 'vocab_tree': return '词汇树匹配'
    default: return props.block.matching_method
  }
})

onMounted(async () => {
  try {
    const response = await resultApi.getStats(props.block.id)
    stats.value = response.data
  } catch {
    // Use block statistics as fallback
    stats.value = props.block.statistics || {}
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
.statistics-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-card {
  position: relative;
  overflow: hidden;
}

.summary-card :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-content {
  z-index: 1;
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

.summary-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.summary-icon {
  color: var(--el-color-primary-light-5);
  opacity: 0.8;
}

.stage-times {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-time-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stage-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.stage-name {
  color: #606266;
}

.stage-value {
  color: #909399;
}

.params-card {
  margin-top: 20px;
}
</style>
