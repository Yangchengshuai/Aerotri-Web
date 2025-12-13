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
      <!-- Summary Comparison -->
      <el-card class="comparison-card">
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
    </div>

    <!-- Empty State -->
    <el-empty v-else-if="completedBlocks.length < 2" description="至少需要两个已完成的 Block 才能进行对比" />
    <el-empty v-else description="请选择两个 Block 进行对比" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import type { Block } from '@/types'
import BlockStats from '@/components/BlockStats.vue'

const router = useRouter()
const blocksStore = useBlocksStore()

const leftBlockId = ref<string | null>(null)
const rightBlockId = ref<string | null>(null)

const completedBlocks = computed(() => {
  return blocksStore.blocks.filter(b => b.status === 'completed')
})

const leftBlock = computed(() => {
  return completedBlocks.value.find(b => b.id === leftBlockId.value) || null
})

const rightBlock = computed(() => {
  return completedBlocks.value.find(b => b.id === rightBlockId.value) || null
})

const comparisonData = computed(() => {
  if (!leftBlock.value || !rightBlock.value) return []

  const left = leftBlock.value.statistics || {}
  const right = rightBlock.value.statistics || {}

  const metrics = [
    {
      metric: '算法',
      leftValue: leftBlock.value.algorithm.toUpperCase(),
      rightValue: rightBlock.value.algorithm.toUpperCase(),
      diff: '-',
    },
    {
      metric: '注册图像数',
      leftValue: left.num_registered_images || '-',
      rightValue: right.num_registered_images || '-',
      leftBetter: (left.num_registered_images || 0) > (right.num_registered_images || 0),
      rightBetter: (right.num_registered_images || 0) > (left.num_registered_images || 0),
      diff: formatDiff((left.num_registered_images || 0) - (right.num_registered_images || 0)),
    },
    {
      metric: '3D 点数',
      leftValue: formatNumber(left.num_points3d),
      rightValue: formatNumber(right.num_points3d),
      leftBetter: (left.num_points3d || 0) > (right.num_points3d || 0),
      rightBetter: (right.num_points3d || 0) > (left.num_points3d || 0),
      diff: formatDiff((left.num_points3d || 0) - (right.num_points3d || 0)),
    },
    {
      metric: '平均重投影误差',
      leftValue: left.mean_reprojection_error?.toFixed(4) || '-',
      rightValue: right.mean_reprojection_error?.toFixed(4) || '-',
      leftBetter: (left.mean_reprojection_error || 999) < (right.mean_reprojection_error || 999),
      rightBetter: (right.mean_reprojection_error || 999) < (left.mean_reprojection_error || 999),
      diff: formatDiff((left.mean_reprojection_error || 0) - (right.mean_reprojection_error || 0), 4),
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

onMounted(async () => {
  await blocksStore.fetchBlocks()
  
  // Auto-select first two completed blocks
  if (completedBlocks.value.length >= 2) {
    leftBlockId.value = completedBlocks.value[0].id
    rightBlockId.value = completedBlocks.value[1].id
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
