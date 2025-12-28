<template>
  <div class="tiles-panel" v-if="block">
    <div class="tiles-header">
      <div class="status">
        <div class="status-line">
          <span>3D Tiles 转换状态：</span>
          <el-tag :type="statusTagType">{{ statusText }}</el-tag>
          <span v-if="currentStageLabel" class="stage-label">
            {{ currentStageLabel }}
          </span>
        </div>
        <div class="status-progress">
          <el-progress
            v-if="tilesStatus"
            :percentage="Math.round(tilesStatus.tiles_progress || 0)"
            :stroke-width="18"
            :text-inside="true"
          />
        </div>
      </div>
      <div class="actions">
        <el-button
          v-if="isRunning"
          type="danger"
          :loading="loadingAction"
          @click="onCancel"
        >
          取消转换
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="loadingAction"
          :disabled="!canStart"
          @click="onStart"
        >
          开始转换
        </el-button>
      </div>
    </div>

    <div class="files-section" v-if="files.length > 0">
      <el-card>
        <template #header>
          <span>转换产物</span>
        </template>
        <el-row :gutter="16">
          <el-col :span="8" v-for="file in files" :key="file.name">
            <el-card class="file-card">
              <div class="file-name">{{ file.name }}</div>
              <div class="file-meta">
                <span>{{ formatSize(file.size_bytes) }}</span>
                <span>·</span>
                <span>{{ formatTime(file.mtime) }}</span>
              </div>
              <div class="file-actions">
                <el-button
                  v-if="file.preview_supported && file.type === 'tileset'"
                  type="primary"
                  text
                  size="small"
                  @click="openPreview(file)"
                >
                  预览
                </el-button>
                <el-button
                  type="primary"
                  text
                  size="small"
                  :href="file.download_url"
                  target="_blank"
                >
                  下载
                </el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-card>
    </div>

    <div class="log-section">
      <el-card>
        <template #header>
          <div class="log-header">
            <span>转换日志</span>
            <div class="log-actions">
              <el-button text size="small" @click="toggleLog">
                {{ showLog ? '收起' : '展开' }}
              </el-button>
              <el-button text size="small" @click="refreshLog">
                手动刷新
              </el-button>
            </div>
          </div>
        </template>
        <el-collapse-transition>
          <div v-show="showLog" class="log-content">
            <el-scrollbar height="260px">
              <pre class="log-text">{{ logText }}</pre>
            </el-scrollbar>
          </div>
        </el-collapse-transition>
      </el-card>
    </div>

    <div class="error-section" v-if="tilesStatus?.tiles_error_message">
      <el-alert
        :title="tilesStatus.tiles_error_message"
        type="error"
        :closable="false"
      />
    </div>

    <!-- 3D Tiles Viewer: Show directly in panel when conversion is completed -->
    <div class="viewer-section" v-if="showViewer && tilesetUrl">
      <el-card class="viewer-card">
        <template #header>
          <div class="viewer-header">
            <span>倾斜模型预览</span>
            <el-button
              text
              size="small"
              @click="showViewer = false"
            >
              收起
            </el-button>
          </div>
        </template>
        <div class="viewer-container">
          <CesiumViewer
            v-if="tilesetUrl"
            :tileset-url="tilesetUrl"
          />
        </div>
      </el-card>
    </div>

    <!-- Fallback: Show viewer button if not auto-displayed -->
    <div class="viewer-action" v-else-if="canShowViewer && !showViewer">
      <el-button
        type="primary"
        @click="loadAndShowViewer"
      >
        显示倾斜模型
      </el-button>
    </div>

    <el-dialog
      v-model="previewVisible"
      title="3D Tiles 预览"
      width="80%"
      top="5vh"
      destroy-on-close
    >
      <CesiumViewer
        v-if="previewTilesetUrl"
        :tileset-url="previewTilesetUrl"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Block, TilesFileInfo } from '@/types'
import { tilesApi } from '@/api'
import CesiumViewer from './CesiumViewer.vue'

const props = defineProps<{
  block: Block
}>()

const loadingAction = ref(false)
const files = ref<TilesFileInfo[]>([])
const logLines = ref<string[]>([])
const showLog = ref(true)
const previewVisible = ref(false)
const previewTilesetUrl = ref<string | null>(null)
const showViewer = ref(false)
const tilesetUrl = ref<string | null>(null)
let statusTimer: number | null = null
let logTimer: number | null = null

const tilesStatus = computed(() => {
  if (!props.block) return null
  return {
    tiles_status: props.block.tiles_status || 'NOT_STARTED',
    tiles_progress: props.block.tiles_progress || 0,
    tiles_current_stage: props.block.tiles_current_stage,
    tiles_output_path: props.block.tiles_output_path,
    tiles_error_message: props.block.tiles_error_message,
    tiles_statistics: props.block.tiles_statistics,
  }
})

const statusText = computed(() => {
  const status = tilesStatus.value?.tiles_status || 'NOT_STARTED'
  const statusMap: Record<string, string> = {
    NOT_STARTED: '未开始',
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '失败',
    CANCELLED: '已取消',
  }
  return statusMap[status] || status
})

const statusTagType = computed(() => {
  const status = tilesStatus.value?.tiles_status || 'NOT_STARTED'
  const typeMap: Record<string, string> = {
    NOT_STARTED: 'info',
    RUNNING: 'warning',
    COMPLETED: 'success',
    FAILED: 'danger',
    CANCELLED: 'info',
  }
  return typeMap[status] || 'info'
})

const currentStageLabel = computed(() => {
  const stage = tilesStatus.value?.tiles_current_stage
  if (!stage) return null
  const stageMap: Record<string, string> = {
    obj_to_glb: 'OBJ → GLB',
    glb_to_tiles: 'GLB → 3D Tiles',
    completed: '已完成',
  }
  return stageMap[stage] || stage
})

const isRunning = computed(() => tilesStatus.value?.tiles_status === 'RUNNING')

const canStart = computed(() => {
  const status = tilesStatus.value?.tiles_status || 'NOT_STARTED'
  return ['NOT_STARTED', 'FAILED', 'CANCELLED', 'COMPLETED'].includes(status)
})

const canShowViewer = computed(() => {
  return tilesStatus.value?.tiles_status === 'COMPLETED' && tilesStatus.value?.tiles_output_path
})

const logText = computed(() => logLines.value.join('\n'))

async function loadStatus() {
  if (!props.block?.id) return

  try {
    const response = await tilesApi.status(props.block.id)
    // Update block in parent component if needed
    // For now, we'll just use the computed value from props
  } catch (err: any) {
    console.error('Failed to load tiles status:', err)
  }
}

async function loadFiles() {
  if (!props.block?.id) return

  try {
    const response = await tilesApi.files(props.block.id)
    files.value = response.data.files
  } catch (err: any) {
    console.error('Failed to load tiles files:', err)
  }
}

async function loadLog() {
  if (!props.block?.id) return

  try {
    const response = await tilesApi.logTail(props.block.id, 200)
    logLines.value = response.data.lines
  } catch (err: any) {
    console.error('Failed to load tiles log:', err)
  }
}

async function onStart() {
  if (!props.block?.id) return

  try {
    loadingAction.value = true
    await tilesApi.convert(props.block.id, {
      keep_glb: false,
      optimize: false,
    })
    ElMessage.success('转换任务已启动')
    // Start polling
    startPolling()
  } catch (err: any) {
    ElMessage.error(`启动转换失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    loadingAction.value = false
  }
}

async function onCancel() {
  if (!props.block?.id) return

  try {
    await ElMessageBox.confirm('确定要取消转换吗？', '确认取消', {
      type: 'warning',
    })
    loadingAction.value = true
    await tilesApi.cancel(props.block.id)
    ElMessage.success('转换已取消')
    stopPolling()
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(`取消转换失败: ${err.response?.data?.detail || err.message}`)
    }
  } finally {
    loadingAction.value = false
  }
}

function toggleLog() {
  showLog.value = !showLog.value
}

function refreshLog() {
  loadLog()
}

async function loadTilesetUrl() {
  if (!props.block?.id) return null

  try {
    const response = await tilesApi.tilesetUrl(props.block.id)
    return response.data.tileset_url
  } catch (err: any) {
    console.error('Failed to load tileset URL:', err)
    return null
  }
}

async function loadAndShowViewer() {
  const url = await loadTilesetUrl()
  if (url) {
    tilesetUrl.value = url
    showViewer.value = true
  } else {
    ElMessage.error('获取 tileset URL 失败')
  }
}

async function openPreview(file: TilesFileInfo) {
  if (file.type !== 'tileset') return

  try {
    const url = await loadTilesetUrl()
    if (url) {
      previewTilesetUrl.value = url
      previewVisible.value = true
    } else {
      ElMessage.error('获取 tileset URL 失败')
    }
  } catch (err: any) {
    ElMessage.error(`获取 tileset URL 失败: ${err.response?.data?.detail || err.message}`)
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN')
}

function startPolling() {
  stopPolling()
  statusTimer = window.setInterval(() => {
    loadStatus()
    loadFiles()
  }, 2000)
  logTimer = window.setInterval(() => {
    loadLog()
  }, 3000)
}

function stopPolling() {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
}

onMounted(() => {
  loadStatus()
  loadFiles()
  loadLog()
  if (isRunning.value) {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})

watch(isRunning, (running) => {
  if (running) {
    startPolling()
  } else {
    stopPolling()
    // Final load
    loadStatus()
    loadFiles()
    loadLog()
    // Auto-load viewer when conversion completes
    if (canShowViewer.value && !showViewer.value) {
      loadAndShowViewer()
    }
  }
})

// Watch for status changes to auto-show viewer when completed
watch(canShowViewer, async (canShow) => {
  if (canShow && !showViewer.value && !isRunning.value) {
    // Auto-load viewer when conversion completes
    await loadAndShowViewer()
  }
}, { immediate: true })
</script>

<style scoped>
.tiles-panel {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tiles-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.status {
  flex: 1;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stage-label {
  color: #909399;
  font-size: 12px;
}

.status-progress {
  width: 300px;
}

.actions {
  display: flex;
  gap: 8px;
}

.files-section {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.file-card {
  margin-bottom: 16px;
}

.file-name {
  font-weight: 500;
  margin-bottom: 8px;
}

.file-meta {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}

.file-actions {
  display: flex;
  gap: 8px;
}

.log-section {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-content {
  margin-top: 12px;
}

.log-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.error-section {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.viewer-section {
  margin-top: 16px;
  margin-bottom: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 允许 flex 子元素缩小 */
}

.viewer-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-section :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  min-height: 0; /* 允许 flex 子元素缩小 */
  display: flex;
  flex-direction: column;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.viewer-container {
  width: 100%;
  flex: 1;
  min-height: 600px;
}

.viewer-action {
  margin-top: 16px;
  text-align: center;
  flex-shrink: 0;
}
</style>

