<template>
  <div class="recon-compare-view">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>重建版本对比</h2>
        <span v-if="blockName" class="block-name">- {{ blockName }}</span>
      </div>
      <div class="header-right">
        <el-button size="small" @click="fetchData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </el-header>

    <!-- Loading state -->
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载中...</p>
    </div>

    <!-- Version Selection -->
    <div v-else class="selection-bar">
      <div class="selector">
        <span class="label">左侧版本:</span>
        <el-select v-model="leftVersionId" placeholder="选择版本" filterable>
          <el-option
            v-for="v in completedVersions"
            :key="v.id"
            :label="`v${v.version_index} - ${v.name}`"
            :value="v.id"
            :disabled="v.id === rightVersionId"
          >
            <div class="version-option">
              <span>v{{ v.version_index }} - {{ v.name }}</span>
              <el-tag size="small" :type="presetTagType(v.quality_preset)">
                {{ presetLabel(v.quality_preset) }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
      <div class="selector">
        <span class="label">右侧版本:</span>
        <el-select v-model="rightVersionId" placeholder="选择版本" filterable>
          <el-option
            v-for="v in completedVersions"
            :key="v.id"
            :label="`v${v.version_index} - ${v.name}`"
            :value="v.id"
            :disabled="v.id === leftVersionId"
          >
            <div class="version-option">
              <span>v{{ v.version_index }} - {{ v.name }}</span>
              <el-tag size="small" :type="presetTagType(v.quality_preset)">
                {{ presetLabel(v.quality_preset) }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- Comparison Content -->
    <div class="comparison-content" v-if="leftVersion && rightVersion">
      <!-- Split Model Viewer -->
      <div class="model-viewer-section">
        <SplitModelViewer
          :left-url="leftModelUrl"
          :right-url="rightModelUrl"
          :left-label="`v${leftVersion.version_index} - ${presetLabel(leftVersion.quality_preset)}`"
          :right-label="`v${rightVersion.version_index} - ${presetLabel(rightVersion.quality_preset)}`"
          :sync-camera="syncCamera"
          @left-loaded="onLeftLoaded"
          @right-loaded="onRightLoaded"
          @left-error="onLeftError"
          @right-error="onRightError"
        />
        <div class="viewer-controls">
          <el-checkbox v-model="syncCamera">
            <el-icon><Link /></el-icon>
            同步视角
          </el-checkbox>
        </div>
      </div>

      <!-- Parameter Comparison Table -->
      <el-card class="comparison-card">
        <template #header>
          <span>参数对比</span>
        </template>
        <el-table :data="paramComparisonData" stripe size="small">
          <el-table-column prop="stage" label="阶段" width="100" />
          <el-table-column prop="param" label="参数" width="140" />
          <el-table-column :label="`v${leftVersion.version_index}`" align="center">
            <template #default="{ row }">
              <span :class="{ 'value-diff': row.leftValue !== row.rightValue }">
                {{ row.leftValue }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="`v${rightVersion.version_index}`" align="center">
            <template #default="{ row }">
              <span :class="{ 'value-diff': row.leftValue !== row.rightValue }">
                {{ row.rightValue }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- Statistics Comparison -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>v{{ leftVersion.version_index }} - {{ leftVersion.name }}</span>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="预设">
                {{ presetLabel(leftVersion.quality_preset) }}
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                {{ leftVersion.status }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatTime(leftVersion.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="完成时间">
                {{ formatTime(leftVersion.completed_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>v{{ rightVersion.version_index }} - {{ rightVersion.name }}</span>
            </template>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="预设">
                {{ presetLabel(rightVersion.quality_preset) }}
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                {{ rightVersion.status }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ formatTime(rightVersion.created_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="完成时间">
                {{ formatTime(rightVersion.completed_at) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- Empty State -->
    <el-empty 
      v-else-if="completedVersions.length < 2" 
      description="至少需要两个已完成的重建版本才能进行对比" 
    />
    <el-empty v-else description="请选择两个版本进行对比" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Loading, Link, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { ReconVersion, ReconstructionParams, ReconFileInfo } from '@/types'
import { reconVersionApi, blockApi } from '@/api'
import SplitModelViewer from '@/components/SplitModelViewer.vue'

const router = useRouter()
const route = useRoute()

const blockId = computed(() => route.params.blockId as string)
const blockName = ref<string>('')
const versions = ref<ReconVersion[]>([])
const loading = ref(true)
const leftVersionId = ref<string | null>(null)
const rightVersionId = ref<string | null>(null)
const syncCamera = ref(true)

// Files for each version
const leftVersionFiles = ref<ReconFileInfo[]>([])
const rightVersionFiles = ref<ReconFileInfo[]>([])

// Get texture model URL (OBJ file) - use the download_url from the API
const leftModelUrl = computed(() => {
  if (!leftVersionId.value) return ''
  const textureFile = leftVersionFiles.value.find(
    f => f.stage === 'texture' && f.name.endsWith('.obj')
  )
  if (textureFile) {
    // The download_url is already a full path like /api/blocks/.../download?file=...
    return textureFile.download_url
  }
  return ''
})

const rightModelUrl = computed(() => {
  if (!rightVersionId.value) return ''
  const textureFile = rightVersionFiles.value.find(
    f => f.stage === 'texture' && f.name.endsWith('.obj')
  )
  if (textureFile) {
    return textureFile.download_url
  }
  return ''
})

const completedVersions = computed(() => {
  return versions.value.filter(v => v.status === 'COMPLETED')
})

const leftVersion = computed(() => {
  return completedVersions.value.find(v => v.id === leftVersionId.value) || null
})

const rightVersion = computed(() => {
  return completedVersions.value.find(v => v.id === rightVersionId.value) || null
})

// Build parameter comparison data
const paramComparisonData = computed(() => {
  if (!leftVersion.value || !rightVersion.value) return []
  
  const leftParams = leftVersion.value.merged_params as ReconstructionParams | null
  const rightParams = rightVersion.value.merged_params as ReconstructionParams | null
  
  if (!leftParams || !rightParams) return []
  
  const data: Array<{
    stage: string
    param: string
    leftValue: string | number
    rightValue: string | number
  }> = []
  
  const stages = ['densify', 'mesh', 'refine', 'texture'] as const
  const stageLabels: Record<string, string> = {
    densify: '稠密化',
    mesh: '网格',
    refine: '优化',
    texture: '纹理',
  }
  
  for (const stage of stages) {
    const leftStageParams = leftParams[stage] as Record<string, unknown> | undefined
    const rightStageParams = rightParams[stage] as Record<string, unknown> | undefined
    
    if (!leftStageParams || !rightStageParams) continue
    
    const allKeys = new Set([
      ...Object.keys(leftStageParams),
      ...Object.keys(rightStageParams),
    ])
    
    for (const key of allKeys) {
      data.push({
        stage: stageLabels[stage] || stage,
        param: key,
        leftValue: leftStageParams[key] as string | number ?? '-',
        rightValue: rightStageParams[key] as string | number ?? '-',
      })
    }
  }
  
  return data
})

async function fetchData() {
  loading.value = true
  try {
    // Fetch block info
    const blockRes = await blockApi.get(blockId.value)
    blockName.value = blockRes.data.name
    
    // Fetch versions
    const versionsRes = await reconVersionApi.list(blockId.value)
    versions.value = versionsRes.data.versions
    
    // Auto-select first two completed versions
    if (completedVersions.value.length >= 2) {
      leftVersionId.value = completedVersions.value[0].id
      rightVersionId.value = completedVersions.value[1].id
    }
  } catch (e) {
    console.error('Failed to fetch data:', e)
  } finally {
    loading.value = false
  }
}

async function fetchVersionFiles(versionId: string, side: 'left' | 'right') {
  try {
    const res = await reconVersionApi.files(blockId.value, versionId)
    if (side === 'left') {
      leftVersionFiles.value = res.data.files
    } else {
      rightVersionFiles.value = res.data.files
    }
  } catch (e) {
    console.error(`Failed to fetch ${side} version files:`, e)
  }
}

function onLeftLoaded() {
  ElMessage.success('左侧模型加载完成')
}

function onRightLoaded() {
  ElMessage.success('右侧模型加载完成')
}

function onLeftError(error: Error) {
  console.error('Left model load error:', error)
  ElMessage.error(`左侧模型加载失败: ${error.message}`)
}

function onRightError(error: Error) {
  console.error('Right model load error:', error)
  ElMessage.error(`右侧模型加载失败: ${error.message}`)
}

function goBack() {
  router.push({ name: 'BlockDetail', params: { id: blockId.value } })
}

function presetTagType(preset: string): '' | 'success' | 'warning' | 'info' {
  switch (preset) {
    case 'fast': return 'warning'
    case 'balanced': return ''
    case 'high': return 'success'
    default: return 'info'
  }
}

function presetLabel(preset: string): string {
  switch (preset) {
    case 'fast': return '快速'
    case 'balanced': return '平衡'
    case 'high': return '高质量'
    default: return preset
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

onMounted(fetchData)

watch(blockId, fetchData)

// Watch for version selection changes to fetch files
watch(leftVersionId, async (newId) => {
  if (newId) {
    await fetchVersionFiles(newId, 'left')
  } else {
    leftVersionFiles.value = []
  }
})

watch(rightVersionId, async (newId) => {
  if (newId) {
    await fetchVersionFiles(newId, 'right')
  } else {
    rightVersionFiles.value = []
  }
})

// Fetch files when versions are initially selected
watch(
  () => completedVersions.value,
  async () => {
    if (leftVersionId.value) {
      await fetchVersionFiles(leftVersionId.value, 'left')
    }
    if (rightVersionId.value) {
      await fetchVersionFiles(rightVersionId.value, 'right')
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.recon-compare-view {
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

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-name {
  color: #909399;
  font-size: 14px;
}

.loading-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #909399;
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

.version-option {
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

.value-diff {
  color: var(--el-color-primary);
  font-weight: 600;
}

.stats-row {
  margin-top: 20px;
}

.model-viewer-section {
  margin-bottom: 20px;
}

.viewer-controls {
  display: flex;
  justify-content: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 0 0 8px 8px;
}
</style>
