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
        <el-button 
          v-if="block?.status === 'running'"
          type="danger"
          @click="handleStop"
        >
          <el-icon><VideoPause /></el-icon>
          停止
        </el-button>
        <el-button
          v-else-if="block?.status !== 'running'"
          type="primary"
          @click="handleRun"
          :disabled="!canRun"
        >
          <el-icon><VideoPlay /></el-icon>
          运行空三
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

          <!-- 3D Viewer Tab -->
          <el-tab-pane label="3D 查看" name="viewer" :disabled="block?.status !== 'completed'">
            <ThreeViewer v-if="block?.status === 'completed'" :block-id="block.id" />
          </el-tab-pane>

          <!-- Statistics Tab -->
          <el-tab-pane label="统计数据" name="stats" :disabled="block?.status !== 'completed'">
            <StatisticsView v-if="block?.status === 'completed'" :block="block" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import { useWebSocket } from '@/composables/useWebSocket'
import { taskApi } from '@/api'
import type { Block, ProgressMessage } from '@/types'

import ImagePreview from '@/components/ImagePreview.vue'
import ParameterSummary from '@/components/ParameterSummary.vue'
import ParameterForm from '@/components/ParameterForm.vue'
import GPUSelector from '@/components/GPUSelector.vue'
import ProgressView from '@/components/ProgressView.vue'
import ThreeViewer from '@/components/ThreeViewer.vue'
import StatisticsView from '@/components/StatisticsView.vue'

const route = useRoute()
const router = useRouter()
const blocksStore = useBlocksStore()

const blockId = computed(() => route.params.id as string)
const block = computed(() => blocksStore.currentBlock)

const activeTab = ref('progress')
const showParamsDialog = ref(false)
const selectedGpuIndex = ref(0)
const imageTotal = ref(0)

// WebSocket for progress updates
const { connected, progress: wsProgress, connect, disconnect } = useWebSocket(blockId.value)

// Computed properties
const statusType = computed(() => {
  switch (block.value?.status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    case 'cancelled': return 'warning'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (block.value?.status) {
    case 'created': return '待处理'
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
}

.main-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
}

:deep(.el-tab-pane) {
  height: 100%;
}
</style>
