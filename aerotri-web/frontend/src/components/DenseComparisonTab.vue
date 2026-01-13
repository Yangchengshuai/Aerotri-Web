<template>
  <div class="dense-comparison-tab">
    <!-- Version Selectors -->
    <div class="version-selectors">
      <div class="version-selector">
        <span class="label">左侧版本:</span>
        <el-select
          v-model="leftVersionId"
          placeholder="选择版本"
          filterable
          :loading="loadingVersions"
          @change="onVersionChange"
        >
          <el-option
            v-for="version in leftVersions"
            :key="version.id"
            :label="versionLabel(version)"
            :value="version.id"
            :disabled="version.status !== 'COMPLETED'"
          >
            <div class="version-option">
              <span>{{ versionLabel(version) }}</span>
              <el-tag
                :type="version.status === 'COMPLETED' ? 'success' : 'info'"
                size="small"
              >
                {{ versionStatusLabel(version.status) }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
      <div class="version-selector">
        <span class="label">右侧版本:</span>
        <el-select
          v-model="rightVersionId"
          placeholder="选择版本"
          filterable
          :loading="loadingVersions"
          @change="onVersionChange"
        >
          <el-option
            v-for="version in rightVersions"
            :key="version.id"
            :label="versionLabel(version)"
            :value="version.id"
            :disabled="version.status !== 'COMPLETED'"
          >
            <div class="version-option">
              <span>{{ versionLabel(version) }}</span>
              <el-tag
                :type="version.status === 'COMPLETED' ? 'success' : 'info'"
                size="small"
              >
                {{ versionStatusLabel(version.status) }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loadingVersions" class="loading-container">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>正在加载重建版本...</p>
    </div>

    <!-- Empty State -->
    <el-empty
      v-else-if="!leftVersions.length && !rightVersions.length"
      description="暂无重建版本数据"
    />

    <!-- Comparison Content -->
    <div v-else-if="leftVersion && rightVersion" class="comparison-content">
      <!-- Dense Reconstruction Metrics -->
      <el-card class="comparison-card">
        <template #header>
          <span>密集重建指标对比</span>
        </template>
        <el-table :data="denseMetrics" stripe>
          <el-table-column prop="metric" label="指标" width="200" />
          <el-table-column :label="leftVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.leftBetter }">{{ row.leftValue }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="rightVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.rightBetter }">{{ row.rightValue }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="diff" label="差异" align="center" width="120" />
        </el-table>
      </el-card>

      <!-- Reconstruction Parameters -->
      <el-card class="comparison-card">
        <template #header>
          <span>重建参数对比</span>
        </template>
        <el-table :data="paramComparison" stripe>
          <el-table-column prop="param" label="参数" width="180" />
          <el-table-column :label="leftVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'param-diff': row.diff !== '相同' }">{{ row.leftValue }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="rightVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'param-diff': row.diff !== '相同' }">{{ row.rightValue }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="diff" label="差异" align="center" width="120" />
        </el-table>
      </el-card>

      <!-- 3D Tiles Statistics -->
      <el-card
        v-if="leftVersion.tiles_status === 'COMPLETED' || rightVersion.tiles_status === 'COMPLETED'"
        class="comparison-card"
      >
        <template #header>
          <span>3D Tiles 转换统计</span>
        </template>
        <el-table :data="tilesMetrics" stripe>
          <el-table-column prop="metric" label="指标" width="200" />
          <el-table-column :label="leftVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.leftBetter }">{{ row.leftValue }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="rightVersionLabel" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.rightBetter }">{{ row.rightValue }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="diff" label="差异" align="center" width="120" />
        </el-table>
      </el-card>
    </div>

    <!-- Incomplete Version Warning -->
    <el-alert
      v-else
      type="warning"
      :closable="false"
      show-icon
      class="warning-alert"
    >
      <template #title>请选择已完成的重建版本进行对比</template>
    </el-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { reconVersionApi, tilesApi } from '@/api'
import type { ReconVersion } from '@/types'

const props = defineProps<{
  leftBlockId: string
  rightBlockId: string
}>()

// State
const leftVersions = ref<ReconVersion[]>([])
const rightVersions = ref<ReconVersion[]>([])
const leftVersionId = ref<string | null>(null)
const rightVersionId = ref<string | null>(null)
const loadingVersions = ref(false)

// Computed
const leftVersion = computed(() => {
  return leftVersions.value.find(v => v.id === leftVersionId.value) || null
})

const rightVersion = computed(() => {
  return rightVersions.value.find(v => v.id === rightVersionId.value) || null
})

const leftVersionLabel = computed(() => {
  return leftVersion.value ? versionLabel(leftVersion.value) : '左侧'
})

const rightVersionLabel = computed(() => {
  return rightVersion.value ? versionLabel(rightVersion.value) : '右侧'
})

// Dense reconstruction metrics
const denseMetrics = computed(() => {
  if (!leftVersion.value || !rightVersion.value) return []

  const left = leftVersion.value
  const right = rightVersion.value

  const metrics = [
    // Processing time
    {
      metric: '总耗时',
      leftValue: formatTime(left.statistics?.total_time),
      rightValue: formatTime(right.statistics?.total_time),
      leftBetter: (left.statistics?.total_time || 999999) < (right.statistics?.total_time || 999999),
      rightBetter: (right.statistics?.total_time || 999999) < (left.statistics?.total_time || 999999),
      diff: formatTimeDiff((left.statistics?.total_time || 0) - (right.statistics?.total_time || 0)),
    },
    // Stage times (if available)
    {
      metric: '稠密化时间',
      leftValue: formatTime(left.statistics?.stage_times?.densify),
      rightValue: formatTime(right.statistics?.stage_times?.densify),
      leftBetter: (left.statistics?.stage_times?.densify || 999999) < (right.statistics?.stage_times?.densify || 999999),
      rightBetter: (right.statistics?.stage_times?.densify || 999999) < (left.statistics?.stage_times?.densify || 999999),
      diff: formatTimeDiff((left.statistics?.stage_times?.densify || 0) - (right.statistics?.stage_times?.densify || 0)),
    },
    {
      metric: '网格重建时间',
      leftValue: formatTime(left.statistics?.stage_times?.mesh),
      rightValue: formatTime(right.statistics?.stage_times?.mesh),
      leftBetter: (left.statistics?.stage_times?.mesh || 999999) < (right.statistics?.stage_times?.mesh || 999999),
      rightBetter: (right.statistics?.stage_times?.mesh || 999999) < (left.statistics?.stage_times?.mesh || 999999),
      diff: formatTimeDiff((left.statistics?.stage_times?.mesh || 0) - (right.statistics?.stage_times?.mesh || 0)),
    },
    {
      metric: '网格优化时间',
      leftValue: formatTime(left.statistics?.stage_times?.refine),
      rightValue: formatTime(right.statistics?.stage_times?.refine),
      leftBetter: (left.statistics?.stage_times?.refine || 999999) < (right.statistics?.stage_times?.refine || 999999),
      rightBetter: (right.statistics?.stage_times?.refine || 999999) < (left.statistics?.stage_times?.refine || 999999),
      diff: formatTimeDiff((left.statistics?.stage_times?.refine || 0) - (right.statistics?.stage_times?.refine || 0)),
    },
    {
      metric: '纹理生成时间',
      leftValue: formatTime(left.statistics?.stage_times?.texture),
      rightValue: formatTime(right.statistics?.stage_times?.texture),
      leftBetter: (left.statistics?.stage_times?.texture || 999999) < (right.statistics?.stage_times?.texture || 999999),
      rightBetter: (right.statistics?.stage_times?.texture || 999999) < (left.statistics?.stage_times?.texture || 999999),
      diff: formatTimeDiff((left.statistics?.stage_times?.texture || 0) - (right.statistics?.stage_times?.texture || 0)),
    },
  ]

  return metrics
})

// Reconstruction parameters comparison
const paramComparison = computed(() => {
  if (!leftVersion.value?.merged_params || !rightVersion.value?.merged_params) return []

  const leftParams = leftVersion.value.merged_params
  const rightParams = rightVersion.value.merged_params
  const leftPreset = leftVersion.value.quality_preset
  const rightPreset = rightVersion.value.quality_preset

  const params = [
    {
      param: '质量预设',
      leftValue: leftPreset.toUpperCase(),
      rightValue: rightPreset.toUpperCase(),
      diff: leftPreset !== rightPreset ? '不同' : '相同',
    },
    {
      param: '稠密化分辨率级别',
      leftValue: leftParams.densify?.resolution_level?.toString() || '-',
      rightValue: rightParams.densify?.resolution_level?.toString() || '-',
      diff: (leftParams.densify?.resolution_level ?? 0) !== (rightParams.densify?.resolution_level ?? 0) ? '不同' : '相同',
    },
    {
      param: '网格分辨率级别',
      leftValue: leftParams.mesh?.resolution_level?.toString() || '-',
      rightValue: rightParams.mesh?.resolution_level?.toString() || '-',
      diff: (leftParams.mesh?.resolution_level ?? 0) !== (rightParams.mesh?.resolution_level ?? 0) ? '不同' : '相同',
    },
    {
      param: '纹理分辨率级别',
      leftValue: leftParams.texture?.resolution_level?.toString() || '-',
      rightValue: rightParams.texture?.resolution_level?.toString() || '-',
      diff: (leftParams.texture?.resolution_level ?? 0) !== (rightParams.texture?.resolution_level ?? 0) ? '不同' : '相同',
    },
  ]

  return params
})

// 3D Tiles metrics
const tilesMetrics = computed(() => {
  if (!leftVersion.value?.tiles_statistics || !rightVersion.value?.tiles_statistics) return []

  const leftStats = leftVersion.value.tiles_statistics as any
  const rightStats = rightVersion.value.tiles_statistics as any

  const metrics = [
    {
      metric: '3D Tiles 状态',
      leftValue: leftVersion.value.tiles_status || 'NOT_STARTED',
      rightValue: rightVersion.value.tiles_status || 'NOT_STARTED',
      diff: leftVersion.value.tiles_status === rightVersion.value.tiles_status ? '相同' : '不同',
    },
    {
      metric: 'B3DM 文件数',
      leftValue: leftStats.b3dm_count?.toLocaleString() || '-',
      rightValue: rightStats.b3dm_count?.toLocaleString() || '-',
      leftBetter: (leftStats.b3dm_count || 0) > (rightStats.b3dm_count || 0),
      rightBetter: (rightStats.b3dm_count || 0) > (leftStats.b3dm_count || 0),
      diff: formatDiff((leftStats.b3dm_count || 0) - (rightStats.b3dm_count || 0)),
    },
    {
      metric: '总文件大小',
      leftValue: formatBytes(leftStats.total_size),
      rightValue: formatBytes(rightStats.total_size),
      leftBetter: (leftStats.total_size || 0) < (rightStats.total_size || 0), // Smaller is better
      rightBetter: (rightStats.total_size || 0) < (leftStats.total_size || 0),
      diff: formatBytesDiff((leftStats.total_size || 0) - (rightStats.total_size || 0)),
    },
  ]

  return metrics
})

// Functions
function versionLabel(version: ReconVersion): string {
  return `${version.name} (${version.quality_preset.toUpperCase()})`
}

function versionStatusLabel(status: string): string {
  const statusMap: Record<string, string> = {
    'PENDING': '等待中',
    'RUNNING': '运行中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'CANCELLED': '已取消',
  }
  return statusMap[status] || status
}

async function loadReconVersions(blockId: string): Promise<ReconVersion[]> {
  try {
    const response = await reconVersionApi.list(blockId)
    return response.data.versions || []
  } catch (err) {
    console.error(`Failed to load recon versions for block ${blockId}:`, err)
    return []
  }
}

function selectLatestCompletedVersion(versions: ReconVersion[]): string | null {
  const completed = versions.filter(v => v.status === 'COMPLETED')
  if (completed.length === 0) return null

  // Sort by completed_at descending
  completed.sort((a, b) => {
    const aTime = a.completed_at ? new Date(a.completed_at).getTime() : 0
    const bTime = b.completed_at ? new Date(b.completed_at).getTime() : 0
    return bTime - aTime
  })

  return completed[0].id
}

function onVersionChange() {
  // Emit event if needed for parent component
  console.log('Version changed:', leftVersionId.value, rightVersionId.value)
}

function formatTime(seconds: number | undefined): string {
  if (seconds === undefined) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function formatTimeDiff(diff: number): string {
  if (Math.abs(diff) < 1) return '相同'
  const sign = diff > 0 ? '+' : ''
  return `${sign}${formatTime(Math.abs(diff))}`
}

function formatDiff(diff: number): string {
  if (diff === 0) return '相同'
  const sign = diff > 0 ? '+' : ''
  return `${sign}${diff.toLocaleString()}`
}

function formatBytes(bytes: number | undefined): string {
  if (bytes === undefined) return '-'
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

function formatBytesDiff(diff: number): string {
  if (Math.abs(diff) < 1024) return '相同'
  const sign = diff > 0 ? '+' : ''
  return `${sign}${formatBytes(Math.abs(diff))}`
}

// Lifecycle
async function loadData() {
  loadingVersions.value = true

  try {
    const [leftVersionsData, rightVersionsData] = await Promise.all([
      loadReconVersions(props.leftBlockId),
      loadReconVersions(props.rightBlockId),
    ])

    leftVersions.value = leftVersionsData
    rightVersions.value = rightVersionsData

    // Auto-select latest completed versions
    leftVersionId.value = selectLatestCompletedVersion(leftVersionsData)
    rightVersionId.value = selectLatestCompletedVersion(rightVersionsData)
  } catch (err) {
    console.error('Failed to load dense comparison data:', err)
  } finally {
    loadingVersions.value = false
  }
}

onMounted(() => {
  loadData()
})

// Watch for block ID changes
watch(() => [props.leftBlockId, props.rightBlockId], () => {
  loadData()
})
</script>

<style scoped>
.dense-comparison-tab {
  padding: 0;
}

.version-selectors {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 20px;
}

.version-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.version-selector .label {
  font-weight: 500;
}

.version-selector .el-select {
  width: 300px;
}

.version-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  color: #909399;
}

.loading-container p {
  margin: 0;
  font-size: 14px;
}

.comparison-content {
  padding: 0 20px 20px 20px;
}

.comparison-card {
  margin-bottom: 20px;
}

.warning-alert {
  margin: 20px;
}

.is-better {
  color: var(--el-color-success);
  font-weight: 600;
}

.param-diff {
  color: var(--el-color-warning);
  font-weight: 600;
}
</style>
