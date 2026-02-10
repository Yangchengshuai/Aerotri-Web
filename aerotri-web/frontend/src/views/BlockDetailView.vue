<template>
  <div class="block-detail-view">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2>{{ block?.name || '加载中...' }}</h2>
        <el-tag :type="statusType" v-if="block">{{ statusText }}</el-tag>
      </div>
      <div class="header-right">
        <!-- 队列状态显示 -->
        <el-tag 
          v-if="block?.status === 'queued'" 
          type="warning"
          size="large"
          class="queue-status-tag"
        >
          排队中 #{{ block?.queue_position }}
        </el-tag>
        
        <el-button 
          v-if="block?.status === 'running'"
          type="danger"
          @click="handleStop"
        >
          <el-icon><VideoPause /></el-icon>
          停止
        </el-button>
        <el-button
          v-else-if="block?.status === 'queued'"
          type="warning"
          @click="handleDequeue"
        >
          <el-icon><Close /></el-icon>
          取消排队
        </el-button>
        <el-button
          v-else-if="block?.current_stage === 'partitions_completed'"
          type="success"
          @click="handleMerge"
        >
          <el-icon><Connection /></el-icon>
          合并分区结果
        </el-button>
        <template v-else-if="block?.status !== 'running' && block?.status !== 'queued'">
          <el-button
            type="primary"
            @click="handleRun"
            :disabled="!canRun"
          >
            <el-icon><VideoPlay /></el-icon>
            立即运行
          </el-button>
          <el-button
            type="warning"
            @click="handleEnqueue"
            :disabled="!canRun"
          >
            <el-icon><Clock /></el-icon>
            加入队列
          </el-button>
        </template>
        <el-button
          v-if="canResumeGlomap"
          type="warning"
          @click="openResumeDialog"
        >
          使用 GLOMAP 继续优化
        </el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <div class="main-content">
      <!-- Left Panel: Block Info & Controls -->
      <el-aside class="left-panel" width="380px">
        <el-scrollbar>
          <!-- Images Section -->
          <el-card class="panel-card">
            <template #header>
              <div class="card-header">
                <span>图像预览</span>
                <el-text type="info">共 {{ imageTotal }} 张</el-text>
              </div>
            </template>
            <ImagePreview
              v-if="block"
              :block-id="block.id"
              @update:total="imageTotal = $event"
            />
          </el-card>

          <!-- Parameters Section -->
          <el-card class="panel-card">
            <template #header>
              <div class="card-header">
                <span>算法参数</span>
                <el-button 
                  type="primary" 
                  link 
                  @click="showParamsDialog = true"
                  :disabled="block?.status === 'running'"
                >
                  配置
                </el-button>
              </div>
            </template>
            <ParameterSummary v-if="block" :block="block" />
          </el-card>

          <!-- Camera List Section (only show when results are available) -->
          <CameraList v-if="canViewResults" />

          <!-- Partition Config Section -->
          <PartitionConfigPanel
            v-if="block"
            :block-id="block.id"
            :block-status="block.status"
          />

          <!-- Partition Status Section -->
          <PartitionList
            v-if="block?.partition_enabled"
            :block-id="block.id"
          />

          <!-- GPU Section -->
          <el-card class="panel-card">
            <template #header>
              <span>GPU 状态</span>
            </template>
            <GPUSelector v-model="selectedGpuIndex" />
          </el-card>
        </el-scrollbar>
      </el-aside>

      <!-- Center Panel: Main View -->
      <el-main class="center-panel">
        <el-tabs v-model="activeTab" class="main-tabs">
          <!-- Progress Tab -->
          <el-tab-pane label="运行进度" name="progress">
            <ProgressView
              v-if="block"
              :block="block"
              :websocket-progress="wsProgress"
            />
          </el-tab-pane>

          <!-- Real-time Visualization Tab (InstantSfM only, when running) -->
          <el-tab-pane 
            label="实时可视化" 
            name="realtime" 
            v-if="block && block.algorithm === 'instantsfm' && block.status === 'running'"
          >
            <InstantSfMRealtimeViewer 
              v-if="block"
              :block-id="block.id" 
            />
          </el-tab-pane>

          <!-- 3D Viewer Tab -->
          <el-tab-pane 
            label="3D 查看" 
            name="viewer" 
            :disabled="!canViewResults"
          >
            <div class="viewer-wrapper" v-if="canViewResults">
              <ThreeViewer 
                :block-id="block.id" 
              />
              <CameraDetailPanel />
            </div>
          </el-tab-pane>

          <!-- Statistics Tab -->
          <el-tab-pane 
            label="统计数据" 
            name="stats" 
            :disabled="!canViewResults"
          >
            <StatisticsView 
              v-if="canViewResults" 
              :block="block" 
            />
          </el-tab-pane>

          <!-- Reconstruction Tab -->
          <el-tab-pane label="重建" name="reconstruction" v-if="block">
            <ReconstructionPanel :block="block" :websocket-progress="wsProgress" />
          </el-tab-pane>

          <!-- 3DGS Tab -->
          <el-tab-pane label="3DGS" name="gs" v-if="block">
            <GaussianSplattingPanel :block="block" />
          </el-tab-pane>

          <!-- 3D Tiles Tab -->
          <el-tab-pane label="3D Tiles" name="tiles" v-if="block">
            <TilesConversionPanel :block="block" />
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </div>

    <!-- Parameters Dialog -->
    <el-dialog
      v-model="showParamsDialog"
      title="算法参数配置"
      width="700px"
      destroy-on-close
    >
      <ParameterForm
        v-if="block"
        :block="block"
        @save="handleSaveParams"
        @cancel="showParamsDialog = false"
      />
    </el-dialog>

    <!-- Resume GLOMAP Dialog -->
    <el-dialog
      v-model="showResumeDialog"
      title="继续优化"
      width="600px"
      destroy-on-close
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        将基于当前空三结果执行一轮 GLOMAP mapper_resume 全局优化
      </el-alert>
      
      <el-form label-width="140px">
        <el-form-item label="输入 COLMAP 目录">
          <el-input
            v-model="resumeInputPath"
            placeholder="留空将自动使用当前空三结果的输出路径"
            clearable
          />
          <el-text type="info" size="small" style="display: block; margin-top: 4px">
            包含 cameras.bin/txt, images.bin/txt, points3D.bin/txt 的 COLMAP 稀疏重建目录
          </el-text>
        </el-form-item>
        
        <el-form-item label="GPU 索引">
          <el-input-number
            v-model="selectedGpuIndex"
            :min="0"
            :max="15"
            :step="1"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showResumeDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGlomapResume" :loading="false">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.viewer-wrapper {
  position: relative;
  height: 100%;
  width: 100%;
  min-height: 600px; /* Ensure minimum height for 3D viewer */
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause, Connection, Clock, Close } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import { useQueueStore } from '@/stores/queue'
import { useWebSocket } from '@/composables/useWebSocket'
import { taskApi, queueApi } from '@/api'
import type { Block, ProgressMessage } from '@/types'

import ImagePreview from '@/components/ImagePreview.vue'
import ParameterSummary from '@/components/ParameterSummary.vue'
import ParameterForm from '@/components/ParameterForm.vue'
import PartitionConfigPanel from '@/components/PartitionConfigPanel.vue'
import PartitionList from '@/components/PartitionList.vue'
import GPUSelector from '@/components/GPUSelector.vue'
import ProgressView from '@/components/ProgressView.vue'
import ThreeViewer from '@/components/ThreeViewer.vue'
import InstantSfMRealtimeViewer from '@/components/InstantSfMRealtimeViewer.vue'
import StatisticsView from '@/components/StatisticsView.vue'
import ReconstructionPanel from '@/components/ReconstructionPanel.vue'
import GaussianSplattingPanel from '@/components/GaussianSplattingPanel.vue'
import TilesConversionPanel from '@/components/TilesConversionPanel.vue'
import CameraList from '@/components/CameraList.vue'
import CameraDetailPanel from '@/components/CameraDetailPanel.vue'

const route = useRoute()
const router = useRouter()
const blocksStore = useBlocksStore()
const queueStore = useQueueStore()

const blockId = computed(() => route.params.id as string)
const block = computed(() => blocksStore.currentBlock)

const activeTab = ref('progress')
const showParamsDialog = ref(false)
const showResumeDialog = ref(false)
const resumeInputPath = ref('')
const selectedGpuIndex = ref(0)
const imageTotal = ref(0)

// WebSocket for progress updates
const { connected, progress: wsProgress, connect, disconnect } = useWebSocket(blockId.value)

// Computed properties
const statusType = computed(() => {
  switch (block.value?.status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'queued': return 'warning'
    case 'failed': return 'danger'
    case 'cancelled': return 'warning'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (block.value?.status) {
    case 'created': return '待处理'
    case 'queued': return '排队中'
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return block.value?.status || ''
  }
})

const canRun = computed(() => {
  return block.value && ['created', 'failed', 'cancelled', 'completed'].includes(block.value.status)
})

const canViewResults = computed(() => {
  if (!block.value) return false
  // For partitioned blocks, allow viewing if partitions are completed (even if not merged yet)
  if (block.value.partition_enabled) {
    return block.value.status === 'completed' || 
           block.value.current_stage === 'partitions_completed' ||
           block.value.current_stage === 'merging'
  }
  // For non-partitioned blocks, require completed status
  return block.value.status === 'completed'
})

// When GLOMAP is used and a first reconstruction has completed, allow starting mapper_resume
const canResumeGlomap = computed(() => {
  if (!block.value) return false
  if (block.value.status !== 'completed') return false
  return block.value.algorithm === 'glomap'
})

// Lifecycle
onMounted(async () => {
  await blocksStore.fetchBlock(blockId.value)
  
  // Connect WebSocket if running
  if (block.value?.status === 'running') {
    connect()
  }
})

onUnmounted(() => {
  disconnect()
})

// Watch for status changes
watch(() => block.value?.status, (status) => {
  if (status === 'running') {
    connect()
  } else {
    disconnect()
  }
  
  // Switch to appropriate tab
  if (status === 'completed') {
    activeTab.value = 'viewer'
  }
})

// Methods
function goBack() {
  router.push({ name: 'Home' })
}

async function handleRun() {
  try {
    await taskApi.run(blockId.value, selectedGpuIndex.value)
    ElMessage.success('任务已提交')
    await blocksStore.fetchBlock(blockId.value)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '提交失败')
  }
}

async function handleEnqueue() {
  try {
    const currentBlock = block.value
    if (!currentBlock) {
      ElMessage.error('Block 信息未加载')
      return
    }

    // Auto-reset if block is not in CREATED status
    if (currentBlock.status !== 'created') {
      await ElMessageBox.confirm(
        `Block 当前状态为 "${getStatusText(currentBlock.status)}"，需要先重置才能加入队列。是否自动重置并加入队列？`,
        '需要重置',
        {
          type: 'info',
          confirmButtonText: '重置并加入队列',
          cancelButtonText: '取消',
        }
      )

      // Reset the block first
      await blocksStore.resetBlock(blockId.value)
      ElMessage.info('已重置，正在加入队列...')
    }

    await queueApi.enqueue(blockId.value)
    ElMessage.success('已加入队列')
    await blocksStore.fetchBlock(blockId.value)
  } catch (e: unknown) {
    if (e !== false) { // false means user cancelled
      ElMessage.error(e instanceof Error ? e.message : '加入队列失败')
    }
  }
}

// Helper function to get status text
function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'created': '待处理',
    'queued': '已入队',
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消',
  }
  return statusMap[status] || status
}

async function handleDequeue() {
  try {
    await ElMessageBox.confirm('确定要从队列中移除此任务吗？', '确认移除', { type: 'warning' })
    await queueApi.dequeue(blockId.value)
    ElMessage.success('已从队列移除')
    await blocksStore.fetchBlock(blockId.value)
  } catch {
    // User cancelled
  }
}

async function handleStop() {
  try {
    await ElMessageBox.confirm('确定要停止当前任务吗？', '确认停止', { type: 'warning' })
    await taskApi.stop(blockId.value)
    ElMessage.success('任务已停止')
    await blocksStore.fetchBlock(blockId.value)
  } catch {
    // User cancelled
  }
}

async function handleMerge() {
  try {
    await ElMessageBox.confirm('确定要合并所有分区结果吗？', '确认合并', { type: 'info' })
    await taskApi.merge(blockId.value)
    ElMessage.success('合并任务已提交')
    await blocksStore.fetchBlock(blockId.value)
  } catch (e: unknown) {
    if (e instanceof Error && e.message !== 'cancel') {
      ElMessage.error(e.message || '合并失败')
    }
  }
}

function openResumeDialog() {
  if (!block.value) return
  // Set default input path
  resumeInputPath.value = block.value.output_path 
    ? `${block.value.output_path}/sparse/0`
    : ''
  showResumeDialog.value = true
}

async function handleGlomapResume() {
  if (!block.value) return
  
  try {
    // Use user-specified path or default
    const inputPath = resumeInputPath.value.trim() || null
    
    // Merge with default values to ensure all skip flags are explicitly set
    // Defaults match GLOMAP GlobalMapperOptions: skip_global_positioning=false, skip_bundle_adjustment=false, skip_pruning=true
    const defaultGlomapResumeParams = {
      skip_global_positioning: false,
      skip_bundle_adjustment: false,
      skip_pruning: true,
    }
    const glomapParams = {
      ...defaultGlomapResumeParams,
      ...(block.value.mapper_params || {}),
    }
    
    const response = await taskApi.glomapMapperResume(blockId.value, {
      gpu_index: selectedGpuIndex.value,
      glomap_params: glomapParams,
      input_colmap_path: inputPath,
    })
    
    // Show success message with child block info
    const childBlockId = response.data.block_id
    const logPath = `/root/work/aerotri-web/data/outputs/${childBlockId}/run.log`
    
    ElMessage.success({
      message: `GLOMAP 优化任务已提交\n子任务 ID: ${childBlockId}\n日志路径: ${logPath}`,
      duration: 5000,
      showClose: true,
    })
    
    showResumeDialog.value = false
    
    // Navigate to child block page
    router.push({ name: 'BlockDetail', params: { id: childBlockId } })
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '提交 GLOMAP 优化失败')
  } finally {
    await blocksStore.fetchBlock(blockId.value)
  }
}

async function handleSaveParams(params: Partial<Block>) {
  try {
    await blocksStore.updateBlock(blockId.value, params)
    ElMessage.success('参数已保存')
    showParamsDialog.value = false
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  }
}

// Polling for status updates (backup for WebSocket)
let pollTimer: number | null = null

watch(() => block.value?.status, (status) => {
  if (status === 'running' && !pollTimer) {
    pollTimer = window.setInterval(async () => {
      await blocksStore.fetchBlock(blockId.value)
    }, 5000)
  } else if (status !== 'running' && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}, { immediate: true })

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<style scoped>
.block-detail-view {
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

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  padding: 16px;
}

.panel-card {
  margin-bottom: 16px;
}

.panel-card:last-child {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.center-panel {
  flex: 1;
  padding: 16px;
  overflow: hidden;
  min-width: 0; /* Allow flex item to shrink below content size */
}

/* Optimize layout for 3D viewer tab */
.center-panel :deep(.el-tab-pane[id="pane-viewer"]) {
  padding: 0 !important;
  height: 100% !important;
}

.main-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
  min-height: 0; /* 允许内容超出时滚动 */
}

:deep(.el-tab-pane) {
  height: auto; /* 改为 auto，允许内容决定高度 */
  min-height: 100%; /* 最小高度保持 100% */
}
</style>
