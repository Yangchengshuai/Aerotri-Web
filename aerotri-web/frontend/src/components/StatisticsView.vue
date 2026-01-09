<template>
  <div class="statistics-view">
    <!-- Summary Cards -->
    <div class="summary-cards">
      <el-card class="summary-card">
        <div class="summary-content">
          <div class="summary-value">{{ registeredUniqueDisplay }}</div>
          <div class="summary-label">
            注册图像数
            <span v-if="registeredSumDisplay !== '-'"
              class="summary-sub">
              (求和 {{ registeredSumDisplay }})
            </span>
          </div>
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

    <!-- Partition Statistics (if partitioned) -->
    <el-card v-if="block.partition_enabled" class="partition-stats-card">
      <template #header>
        <span>分区统计</span>
      </template>
      <div v-if="loadingPartitions" class="loading-container">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="partitionStats.length === 0" class="empty-container">
        <el-empty description="暂无分区统计数据" />
      </div>
      <el-collapse v-else v-model="expandedPartitions">
        <el-collapse-item
          v-for="partition in partitionStats"
          :key="partition.index"
          :name="partition.index"
        >
          <template #title>
            <div class="partition-header">
              <el-tag>{{ partition.name }}</el-tag>
              <span class="partition-summary">
                {{ partition.statistics?.num_registered_images || 0 }} 相机,
                {{ formatNumber(partition.statistics?.num_points3d || 0) }} 点
              </span>
              <el-tag
                :type="partition.status === 'COMPLETED' ? 'success' : 'info'"
                size="small"
                style="margin-left: 8px"
              >
                {{ partition.status === 'COMPLETED' ? '已完成' : partition.status || '未知' }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="注册图像数">
              {{ partition.statistics?.num_registered_images || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="3D 点数">
              {{ formatNumber(partition.statistics?.num_points3d) }}
            </el-descriptions-item>
            <el-descriptions-item label="观测数">
              {{ formatNumber(partition.statistics?.num_observations) }}
            </el-descriptions-item>
            <el-descriptions-item label="平均重投影误差">
              {{ partition.statistics?.mean_reprojection_error?.toFixed(4) || '-' }} px
            </el-descriptions-item>
            <el-descriptions-item label="平均轨迹长度">
              {{ partition.statistics?.mean_track_length?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="图像数量">
              {{ partition.image_count }}
            </el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- Algorithm Parameters -->
    <el-card class="params-card">
      <template #header>
        <span>算法参数</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="算法">
          {{ algorithmLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="匹配方法">
          {{ matchingMethodLabel }}
        </el-descriptions-item>
        <el-descriptions-item label="GPU Index" v-if="block.algorithm !== 'openmvg_global'">
          {{ algorithmParams.gpu_index ?? 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="特征密度" v-if="block.algorithm === 'openmvg_global'">
          {{ block.openmvg_params?.feature_preset || 'NORMAL' }}
        </el-descriptions-item>
        <el-descriptions-item label="最大图像尺寸" v-if="block.algorithm !== 'openmvg_global'">
          {{ block.feature_params?.max_image_size || 2640 }}
        </el-descriptions-item>
        <el-descriptions-item label="几何模型" v-if="block.algorithm === 'openmvg_global'">
          {{ block.openmvg_params?.geometric_model === 'e' ? 'Essential' : 'Fundamental' }}
        </el-descriptions-item>
        <el-descriptions-item label="最大特征数" v-if="block.algorithm !== 'openmvg_global'">
          {{ block.feature_params?.max_num_features || 20000 }}
        </el-descriptions-item>
        <el-descriptions-item label="距离比率" v-if="block.algorithm === 'openmvg_global'">
          {{ block.openmvg_params?.ratio ?? 0.8 }}
        </el-descriptions-item>
        <el-descriptions-item label="相机模型">
          {{ block.algorithm === 'openmvg_global' ? openmvgCameraModelLabel : (block.feature_params?.camera_model || 'SIMPLE_RADIAL') }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Camera, Location, View, Timer } from '@element-plus/icons-vue'
import type { Block, BlockStatistics } from '@/types'
import { resultApi, partitionApi } from '@/api'

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
const partitionStats = ref<Array<{
  index: number
  name: string
  status: string | null
  image_count: number
  statistics?: {
    num_registered_images?: number
    num_points3d?: number
    num_observations?: number
    mean_reprojection_error?: number
    mean_track_length?: number
  } | null
}>>([])
const loadingPartitions = ref(false)
const expandedPartitions = ref<number[]>([])

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
  const registered = stats.value.num_registered_images_unique ?? stats.value.num_registered_images ?? 0
  const total = stats.value.num_images || registered
  if (total === 0) return '-'
  return `${((registered / total) * 100).toFixed(1)}%`
})

const registeredUniqueDisplay = computed(() => {
  const v = stats.value.num_registered_images_unique ?? stats.value.num_registered_images
  return v === undefined ? '-' : v.toLocaleString()
})

const registeredSumDisplay = computed(() => {
  const v = stats.value.num_registered_images_sum
  return v === undefined ? '-' : v.toLocaleString()
})

const algorithmLabel = computed(() => {
  switch (props.block.algorithm) {
    case 'glomap': return 'GLOMAP'
    case 'colmap': return 'COLMAP'
    case 'instantsfm': return 'InstantSfM'
    case 'openmvg_global': return 'OpenMVG'
    default: return props.block.algorithm
  }
})

const matchingMethodLabel = computed(() => {
  // OpenMVG uses different matching method names
  if (props.block.algorithm === 'openmvg_global') {
    const pairMode = props.block.openmvg_params?.pair_mode || 'EXHAUSTIVE'
    const matchingMethod = props.block.openmvg_params?.matching_method || 'AUTO'
    if (pairMode === 'EXHAUSTIVE') {
      return `穷举配对 + ${matchingMethod}`
    } else {
      return `连续配对 + ${matchingMethod}`
    }
  }
  // COLMAP/GLOMAP/InstantSfM matching methods
  switch (props.block.matching_method) {
    case 'sequential': return '序列匹配'
    case 'exhaustive': return '穷举匹配'
    case 'vocab_tree': return '词汇树匹配'
    case 'spatial': return '空间匹配'
    default: return props.block.matching_method
  }
})

const openmvgCameraModelLabel = computed(() => {
  const model = props.block.openmvg_params?.camera_model || 3
  switch (model) {
    case 1: return 'Pinhole'
    case 2: return 'Pinhole radial 1'
    case 3: return 'Pinhole radial 3'
    case 4: return 'Pinhole brown 2'
    default: return `Model ${model}`
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
  
  // Load partition statistics if partitioned
  if (props.block.partition_enabled) {
    await loadPartitionStats()
  }
})

async function loadPartitionStats() {
  loadingPartitions.value = true
  try {
    const response = await partitionApi.getStatus(props.block.id)
    partitionStats.value = (response.data.partitions || [])
      .filter((p: any) => p.status === 'COMPLETED')
      .map((p: any) => ({
        index: p.index,
        name: p.name,
        status: p.status,
        image_count: p.image_count,
        statistics: p.statistics,
      }))
  } catch (e) {
    console.error('Failed to load partition stats:', e)
  } finally {
    loadingPartitions.value = false
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

.summary-sub {
  margin-left: 6px;
  font-size: 12px;
  color: #b0b3b8;
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

.partition-stats-card {
  margin-top: 20px;
}

.partition-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.partition-summary {
  flex: 1;
  color: #606266;
  font-size: 13px;
}

.loading-container,
.empty-container {
  padding: 20px;
  text-align: center;
}
</style>
