<template>
  <div class="compare-view">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>Block 对比</h2>
      </div>
    </el-header>

    <!-- Block Selection -->
    <div class="selection-bar">
      <div class="selector">
        <span class="label">左侧 Block:</span>
        <el-select v-model="leftBlockId" placeholder="选择 Block" filterable>
          <el-option
            v-for="block in completedBlocks"
            :key="block.id"
            :label="block.name"
            :value="block.id"
            :disabled="block.id === rightBlockId"
          >
            <div class="block-option">
              <span>{{ block.name }}</span>
              <el-tag size="small">{{ block.algorithm.toUpperCase() }}</el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
      <div class="selector">
        <span class="label">右侧 Block:</span>
        <el-select v-model="rightBlockId" placeholder="选择 Block" filterable>
          <el-option
            v-for="block in completedBlocks"
            :key="block.id"
            :label="block.name"
            :value="block.id"
            :disabled="block.id === leftBlockId"
          >
            <div class="block-option">
              <span>{{ block.name }}</span>
              <el-tag size="small">{{ block.algorithm.toUpperCase() }}</el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- Comparison Content -->
    <div class="comparison-content" v-if="leftBlock && rightBlock">
      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="comparison-tabs">
        <!-- Sparse Reconstruction Tab -->
        <el-tab-pane label="稀疏重建对比" name="sparse">
          <!-- Parameter Consistency Warning -->
          <el-alert
            v-if="consistencyWarning && !loading"
            type="warning"
            :closable="false"
            show-icon
            class="consistency-warning"
          >
            <template #title>
              <span>⚠️ 参数不一致: {{ consistencyWarning }}</span>
            </template>
            <template #default>
              <span>对比结果可能包含参数差异的影响，请谨慎解读。建议使用相同参数进行对比以获得准确的算法性能对比。</span>
            </template>
          </el-alert>

          <!-- Loading State -->
          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <p>正在加载统计数据...</p>
          </div>

          <!-- Error State -->
          <el-alert
            v-else-if="error"
            type="error"
            :closable="false"
            show-icon
            class="error-alert"
          >
            <template #title>加载失败</template>
            <template #default>{{ error }}</template>
          </el-alert>

          <!-- Summary Comparison -->
          <el-card v-else class="comparison-card">
        <template #header>
          <span>对比概览</span>
        </template>
        <el-table :data="comparisonData" stripe>
          <el-table-column prop="metric" label="指标" width="180" />
          <el-table-column :label="leftBlock.name" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.leftBetter }">{{ row.leftValue }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="rightBlock.name" align="center">
            <template #default="{ row }">
              <span :class="{ 'is-better': row.rightBetter }">{{ row.rightValue }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="diff" label="差异" align="center" width="120" />
        </el-table>
      </el-card>

      <!-- Side by Side Stats -->
      <el-row :gutter="20" class="side-by-side">
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="block-header">
                <span>{{ leftBlock.name }}</span>
                <el-tag>{{ leftBlock.algorithm.toUpperCase() }}</el-tag>
              </div>
            </template>
            <BlockStats :block="leftBlock" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <div class="block-header">
                <span>{{ rightBlock.name }}</span>
                <el-tag>{{ rightBlock.algorithm.toUpperCase() }}</el-tag>
              </div>
            </template>
            <BlockStats :block="rightBlock" />
          </el-card>
        </el-col>
      </el-row>
        </el-tab-pane>

        <!-- Dense Reconstruction Tab -->
        <el-tab-pane label="密集重建对比" name="dense">
          <DenseComparisonTab
            v-if="leftBlockId && rightBlockId"
            :left-block-id="leftBlockId"
            :right-block-id="rightBlockId"
          />
        </el-tab-pane>

        <!-- 3D Model Tab -->
        <el-tab-pane label="3D模型对比" name="model">
          <!-- Loading state for models -->
          <div v-if="loadingModels" class="loading-container">
            <el-icon class="is-loading" :size="32"><Loading /></el-icon>
            <p>正在加载 3D 模型...</p>
          </div>

          <!-- Error state -->
          <el-alert
            v-else-if="modelError"
            type="error"
            :closable="false"
            show-icon
            class="error-alert"
          >
            <template #title>{{ modelError }}</template>
          </el-alert>

          <!-- 3D Model Comparison -->
          <BrushCompareViewer
            v-else-if="leftTilesetUrl && rightTilesetUrl"
            :left-tileset-url="leftTilesetUrl"
            :right-tileset-url="rightTilesetUrl"
            :left-label="leftBlock?.name || '左侧'"
            :right-label="rightBlock?.name || '右侧'"
            @left-loaded="onLeftModelLoaded"
            @right-loaded="onRightModelLoaded"
            @error="onModelError"
          />

          <!-- No models available -->
          <el-empty
            v-else
            description="暂无 3D Tiles 数据，请先完成密集重建和 3D Tiles 转换"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Empty State -->
    <el-empty v-else-if="completedBlocks.length < 2" description="至少需要两个已完成的 Block 才能进行对比" />
    <el-empty v-else description="请选择两个 Block 进行对比" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import { resultApi, reconVersionApi, tilesApi } from '@/api'
import type { Block, BlockStatistics } from '@/types'
import BlockStats from '@/components/BlockStats.vue'
import DenseComparisonTab from '@/components/DenseComparisonTab.vue'
import BrushCompareViewer from '@/components/BrushCompareViewer.vue'

const router = useRouter()
const route = useRoute()
const blocksStore = useBlocksStore()

const activeTab = ref('sparse')
const leftBlockId = ref<string | null>(null)
const rightBlockId = ref<string | null>(null)
const leftStats = ref<BlockStatistics | null>(null)
const rightStats = ref<BlockStatistics | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// 3D Model state
const loadingModels = ref(false)
const modelError = ref<string | null>(null)
const leftTilesetUrl = ref<string | null>(null)
const rightTilesetUrl = ref<string | null>(null)

const completedBlocks = computed(() => {
  return blocksStore.blocks.filter(b => b.status === 'completed')
})

const leftBlock = computed(() => {
  return completedBlocks.value.find(b => b.id === leftBlockId.value) || null
})

const rightBlock = computed(() => {
  return completedBlocks.value.find(b => b.id === rightBlockId.value) || null
})

// 参数一致性检查
const consistencyWarning = computed(() => {
  if (!leftBlock.value || !rightBlock.value) return null

  const warnings: string[] = []

  // 检查算法类型
  if (leftBlock.value.algorithm !== rightBlock.value.algorithm) {
    warnings.push(`算法类型不一致 (${leftBlock.value.algorithm.toUpperCase()} vs ${rightBlock.value.algorithm.toUpperCase()})`)
  }

  // 检查匹配方法
  if (leftBlock.value.matching_method !== rightBlock.value.matching_method) {
    warnings.push(`匹配方法不一致 (${leftBlock.value.matching_method} vs ${rightBlock.value.matching_method})`)
  }

  // 检查重建参数
  if (leftStats.value?.algorithm_params?.recon_params && rightStats.value?.algorithm_params?.recon_params) {
    const leftParams = leftStats.value.algorithm_params.recon_params as any
    const rightParams = rightStats.value.algorithm_params.recon_params as any
    if (leftParams.quality_preset !== rightParams.quality_preset) {
      warnings.push(`重建参数不一致 (${leftParams.quality_preset || 'custom'} vs ${rightParams.quality_preset || 'custom'})`)
    }
  }

  return warnings.length > 0 ? warnings.join('; ') : null
})

const comparisonData = computed(() => {
  if (!leftStats.value || !rightStats.value) return []

  const left = leftStats.value
  const right = rightStats.value
  const leftBlockData = leftBlock.value!
  const rightBlockData = rightBlock.value!

  const metrics = [
    // 基础信息
    {
      metric: '算法',
      leftValue: leftBlockData.algorithm.toUpperCase(),
      rightValue: rightBlockData.algorithm.toUpperCase(),
      diff: leftBlockData.algorithm !== rightBlockData.algorithm ? '不同' : '相同',
    },
    {
      metric: '匹配方法',
      leftValue: leftBlockData.matching_method,
      rightValue: rightBlockData.matching_method,
      diff: leftBlockData.matching_method !== rightBlockData.matching_method ? '不同' : '相同',
    },
    // 稀疏重建质量指标
    {
      metric: '总图像数',
      leftValue: left.num_images?.toLocaleString() || '-',
      rightValue: right.num_images?.toLocaleString() || '-',
      diff: formatDiff((left.num_images || 0) - (right.num_images || 0)),
    },
    {
      metric: '注册图像数',
      leftValue: left.num_registered_images?.toLocaleString() || '-',
      rightValue: right.num_registered_images?.toLocaleString() || '-',
      leftBetter: (left.num_registered_images || 0) > (right.num_registered_images || 0),
      rightBetter: (right.num_registered_images || 0) > (left.num_registered_images || 0),
      diff: formatDiff((left.num_registered_images || 0) - (right.num_registered_images || 0)),
    },
    {
      metric: '3D 点云数',
      leftValue: left.num_points3d?.toLocaleString() || '-',
      rightValue: right.num_points3d?.toLocaleString() || '-',
      leftBetter: (left.num_points3d || 0) > (right.num_points3d || 0),
      rightBetter: (right.num_points3d || 0) > (left.num_points3d || 0),
      diff: formatDiff((left.num_points3d || 0) - (right.num_points3d || 0)),
    },
    {
      metric: '平均重投影误差 (px)',
      leftValue: left.mean_reprojection_error?.toFixed(4) || '-',
      rightValue: right.mean_reprojection_error?.toFixed(4) || '-',
      leftBetter: (left.mean_reprojection_error || 999) < (right.mean_reprojection_error || 999),
      rightBetter: (right.mean_reprojection_error || 999) < (left.mean_reprojection_error || 999),
      diff: formatDiff((left.mean_reprojection_error || 0) - (right.mean_reprojection_error || 0), 4),
    },
    {
      metric: '平均轨迹长度',
      leftValue: left.mean_track_length?.toFixed(2) || '-',
      rightValue: right.mean_track_length?.toFixed(2) || '-',
      leftBetter: (left.mean_track_length || 0) > (right.mean_track_length || 0),
      rightBetter: (right.mean_track_length || 0) > (left.mean_track_length || 0),
      diff: formatDiff((left.mean_track_length || 0) - (right.mean_track_length || 0), 2),
    },
    // 处理性能指标
    {
      metric: '特征提取时间',
      leftValue: formatTime(left.stage_times?.feature_extraction),
      rightValue: formatTime(right.stage_times?.feature_extraction),
      leftBetter: (left.stage_times?.feature_extraction || 999999) < (right.stage_times?.feature_extraction || 999999),
      rightBetter: (right.stage_times?.feature_extraction || 999999) < (left.stage_times?.feature_extraction || 999999),
      diff: formatTimeDiff((left.stage_times?.feature_extraction || 0) - (right.stage_times?.feature_extraction || 0)),
    },
    {
      metric: '匹配时间',
      leftValue: formatTime(left.stage_times?.matching),
      rightValue: formatTime(right.stage_times?.matching),
      leftBetter: (left.stage_times?.matching || 999999) < (right.stage_times?.matching || 999999),
      rightBetter: (right.stage_times?.matching || 999999) < (left.stage_times?.matching || 999999),
      diff: formatTimeDiff((left.stage_times?.matching || 0) - (right.stage_times?.matching || 0)),
    },
    {
      metric: 'Mapping 时间',
      leftValue: formatTime(left.stage_times?.mapping),
      rightValue: formatTime(right.stage_times?.mapping),
      leftBetter: (left.stage_times?.mapping || 999999) < (right.stage_times?.mapping || 999999),
      rightBetter: (right.stage_times?.mapping || 999999) < (left.stage_times?.mapping || 999999),
      diff: formatTimeDiff((left.stage_times?.mapping || 0) - (right.stage_times?.mapping || 0)),
    },
    {
      metric: '总耗时',
      leftValue: formatTime(left.total_time),
      rightValue: formatTime(right.total_time),
      leftBetter: (left.total_time || 999999) < (right.total_time || 999999),
      rightBetter: (right.total_time || 999999) < (left.total_time || 999999),
      diff: formatTimeDiff((left.total_time || 0) - (right.total_time || 0)),
    },
  ]

  return metrics
})

// 加载统计数据函数
async function loadBlockStats(blockId: string): Promise<BlockStatistics | null> {
  try {
    const response = await resultApi.getStats(blockId)
    return response.data
  } catch (err) {
    console.error(`Failed to load stats for block ${blockId}:`, err)
    return null
  }
}

async function loadComparisonData() {
  if (!leftBlockId.value || !rightBlockId.value) return

  loading.value = true
  error.value = null

  try {
    const [leftStatsData, rightStatsData] = await Promise.all([
      loadBlockStats(leftBlockId.value),
      loadBlockStats(rightBlockId.value),
    ])

    leftStats.value = leftStatsData
    rightStats.value = rightStatsData
  } catch (err) {
    error.value = err?.message || '加载失败'
    console.error('Failed to load comparison data:', err)
  } finally {
    loading.value = false
  }
}

function selectDefaultBlocks() {
  if (completedBlocks.value.length < 2) return

  const blocksByAlgorithm: Record<string, Block[]> = {}
  completedBlocks.value.forEach(block => {
    if (!blocksByAlgorithm[block.algorithm]) {
      blocksByAlgorithm[block.algorithm] = []
    }
    blocksByAlgorithm[block.algorithm].push(block)
  })

  const algorithms = Object.keys(blocksByAlgorithm)
  if (algorithms.length >= 2) {
    leftBlockId.value = blocksByAlgorithm[algorithms[0]][0].id
    rightBlockId.value = blocksByAlgorithm[algorithms[1]][0].id
  } else {
    leftBlockId.value = completedBlocks.value[0].id
    rightBlockId.value = completedBlocks.value[1].id
  }
}

onMounted(async () => {
  await blocksStore.fetchBlocks()

  // 检查 URL query 参数
  const { left, right } = route.query
  if (left && right && typeof left === 'string' && typeof right === 'string') {
    // 验证 Block ID 是否存在
    const leftExists = completedBlocks.value.find(b => b.id === left)
    const rightExists = completedBlocks.value.find(b => b.id === right)

    if (leftExists && rightExists) {
      leftBlockId.value = left
      rightBlockId.value = right
    } else {
      // 如果指定的 Block 不存在，使用默认选择
      selectDefaultBlocks()
    }
  } else {
    // 默认选择：尽量选择不同算法的 Block
    selectDefaultBlocks()
  }

  // 加载统计数据
  if (leftBlockId.value && rightBlockId.value) {
    await loadComparisonData()
  }
})

// 监听 Block ID 变化，重新加载数据
watch([leftBlockId, rightBlockId], () => {
  if (leftBlockId.value && rightBlockId.value) {
    loadComparisonData()
  }

  // Reset model state when blocks change
  leftTilesetUrl.value = null
  rightTilesetUrl.value = null
  modelError.value = null

  // Reload models if we're on the model tab
  if (activeTab.value === 'model') {
    load3DModels()
  }
})

function goBack() {
  router.push({ name: 'Home' })
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

function formatDiff(diff: number, decimals = 0): string {
  if (diff === 0) return '相同'
  const sign = diff > 0 ? '+' : ''
  if (decimals > 0) {
    return `${sign}${diff.toFixed(decimals)}`
  }
  return `${sign}${diff.toLocaleString()}`
}

function formatTimeDiff(diff: number): string {
  if (Math.abs(diff) < 1) return '相同'
  const sign = diff > 0 ? '+' : ''
  return `${sign}${formatTime(Math.abs(diff))}`
}

// ==================== 3D Model Loading ====================

async function getLatestCompletedVersionWithTiles(blockId: string): Promise<{ versionId: string | null, tilesetUrl: string | null }> {
  try {
    // Get all recon versions
    const versionsRes = await reconVersionApi.list(blockId)
    const versions = versionsRes.data.versions || []

    // Filter completed versions
    const completed = versions.filter(v => v.status === 'COMPLETED')
    if (completed.length === 0) {
      return { versionId: null, tilesetUrl: null }
    }

    // Sort by completed_at descending
    completed.sort((a, b) => {
      const aTime = a.completed_at ? new Date(a.completed_at).getTime() : 0
      const bTime = b.completed_at ? new Date(b.completed_at).getTime() : 0
      return bTime - aTime
    })

    // Find first version with completed 3D Tiles
    for (const version of completed) {
      if (version.tiles_status === 'COMPLETED') {
        try {
          const tilesetRes = await tilesApi.versionTilesetUrl(blockId, version.id)
          return {
            versionId: version.id,
            tilesetUrl: tilesetRes.data.tileset_url
          }
        } catch (err) {
          console.warn(`Failed to get tileset URL for version ${version.id}:`, err)
          continue
        }
      }
    }

    return { versionId: null, tilesetUrl: null }
  } catch (err) {
    console.error(`Failed to get version with tiles for block ${blockId}:`, err)
    return { versionId: null, tilesetUrl: null }
  }
}

async function load3DModels() {
  if (!leftBlockId.value || !rightBlockId.value) return

  loadingModels.value = true
  modelError.value = null

  try {
    const [leftResult, rightResult] = await Promise.all([
      getLatestCompletedVersionWithTiles(leftBlockId.value),
      getLatestCompletedVersionWithTiles(rightBlockId.value),
    ])

    leftTilesetUrl.value = leftResult.tilesetUrl
    rightTilesetUrl.value = rightResult.tilesetUrl

    if (!leftResult.tilesetUrl && !rightResult.tilesetUrl) {
      modelError.value = '两个 Block 都没有可用的 3D Tiles 数据'
    } else if (!leftResult.tilesetUrl) {
      modelError.value = '左侧 Block 没有可用的 3D Tiles 数据'
    } else if (!rightResult.tilesetUrl) {
      modelError.value = '右侧 Block 没有可用的 3D Tiles 数据'
    }
  } catch (err: any) {
    modelError.value = err?.message || '加载 3D 模型失败'
    console.error('Failed to load 3D models:', err)
  } finally {
    loadingModels.value = false
  }
}

function onLeftModelLoaded() {
  console.log('Left model loaded')
}

function onRightModelLoaded() {
  console.log('Right model loaded')
}

function onModelError(error: string) {
  console.error('Model error:', error)
  modelError.value = error
}

// Watch for tab changes to lazy-load 3D models
watch(activeTab, async (newTab) => {
  if (newTab === 'model' && !leftTilesetUrl.value && !rightTilesetUrl.value) {
    await load3DModels()
  }
})
</script>

<style scoped>
.compare-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 24px;
  height: 64px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 18px;
}

.selection-bar {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selector .label {
  font-weight: 500;
}

.selector .el-select {
  width: 300px;
}

.block-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.comparison-content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.comparison-card {
  margin-bottom: 20px;
}

.consistency-warning {
  margin-bottom: 20px;
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

.error-alert {
  margin-bottom: 20px;
}

.is-better {
  color: var(--el-color-success);
  font-weight: 600;
}

.side-by-side {
  margin-top: 20px;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
