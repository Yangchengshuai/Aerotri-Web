<template>
  <div class="recon-panel" v-if="block">
    <div class="recon-header">
      <div class="status">
        <div class="status-line">
          <span>重建状态：</span>
          <el-tag :type="statusTagType">{{ statusText }}</el-tag>
          <span v-if="currentStageLabel" class="stage-label">
            {{ currentStageLabel }}
          </span>
        </div>
        <div class="status-progress">
          <el-progress
            v-if="state"
            :percentage="Math.round(state.progress)"
            :stroke-width="18"
            :text-inside="true"
          />
          <div
            v-if="reconWsMessage"
            class="status-message"
          >
            {{ reconWsMessage }}
          </div>
        </div>
      </div>
      <div class="actions">
        <el-select
          v-model="qualityPreset"
          size="small"
          style="width: 160px; margin-right: 12px"
        >
          <el-option label="快速 (fast)" value="fast" />
          <el-option label="平衡 (balanced)" value="balanced" />
          <el-option label="高质量 (high)" value="high" />
        </el-select>
        <el-button
          v-if="isRunning"
          type="danger"
          :loading="loadingAction"
          @click="onCancel"
        >
          中止重建
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="loadingAction"
          :disabled="!canStart"
          @click="onStart"
        >
          开始重建
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="stage-row">
      <el-col :span="6" v-for="card in stageCards" :key="card.stage">
        <el-card class="stage-card">
          <template #header>
            <div class="card-header">
              <span>{{ card.title }}</span>
              <el-tag :type="card.tagType" size="small">
                {{ card.statusText }}
              </el-tag>
            </div>
          </template>
          <div class="card-body">
            <div v-if="card.file">
              <div class="file-name">{{ card.file.name }}</div>
              <div class="file-meta">
                <span>{{ formatSize(card.file.size_bytes) }}</span>
                <span>·</span>
                <span>{{ formatTime(card.file.mtime) }}</span>
              </div>
              <div class="card-actions">
                <el-button
                  v-if="card.file.preview_supported"
                  type="primary"
                  text
                  size="small"
                  @click="openPreview(card.file)"
                >
                  预览
                </el-button>
                <el-button
                  type="primary"
                  text
                  size="small"
                  :href="card.file.download_url"
                  target="_blank"
                >
                  下载
                </el-button>
              </div>
            </div>
            <div v-else class="empty">
              <el-text type="info">尚未生成输出</el-text>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="log-section">
      <el-card>
        <template #header>
          <div class="log-header">
            <span>重建日志</span>
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

    <div class="error-section" v-if="block.recon_error_message">
      <h4>最近错误</h4>
      <pre class="error-box">{{ block.recon_error_message }}</pre>
    </div>

    <div class="debug-section" v-if="block">
      <h4>调试信息</h4>
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="Block ID">
          <code>{{ block.id }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="SfM 输出目录">
          <code>{{ block.output_path || '暂无（尚未运行空三）' }}</code>
        </el-descriptions-item>
        <el-descriptions-item label="重建输出目录">
          <code>{{ block.recon_output_path || '暂无（尚未重建）' }}</code>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <el-dialog
      v-model="previewVisible"
      title="重建结果预览"
      width="70%"
      top="5vh"
      destroy-on-close
    >
      <ReconstructionViewer
        v-if="previewFile"
        :file-url="previewFile.download_url"
        :file-type="previewFile.type"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Block, ReconFileInfo, ReconstructionState, ProgressMessage } from '@/types'
import { useBlocksStore } from '@/stores/blocks'
import { reconstructionApi } from '@/api'
import ReconstructionViewer from './ReconstructionViewer.vue'

const props = defineProps<{
  block: Block
  websocketProgress?: ProgressMessage | null
}>()

const blocksStore = useBlocksStore()

const qualityPreset = ref<'fast' | 'balanced' | 'high'>('balanced')
const previewVisible = ref(false)
const previewFile = ref<ReconFileInfo | null>(null)
const loadingAction = ref(false)
const logLines = ref<string[]>([])
const showLog = ref(true)
let logTimer: number | null = null

const state = computed<ReconstructionState>(() =>
  blocksStore.getReconstructionState(props.block.id),
)

const isRunning = computed(() => state.value.status === 'RUNNING')

const canStart = computed(() => {
  return ['NOT_STARTED', 'FAILED', 'CANCELLED', 'COMPLETED'].includes(
    state.value.status,
  )
})

const currentStageLabel = computed(() => {
  const stage = state.value.currentStage
  switch (stage) {
    case 'undistort':
      return 'COLMAP 去畸变 (image_undistorter)'
    case 'convert':
      return 'InterfaceCOLMAP'
    case 'densify':
      return 'DensifyPointCloud'
    case 'mesh':
      return 'ReconstructMesh'
    case 'refine':
      return 'RefineMesh'
    case 'texture':
      return 'TextureMesh'
    case 'completed':
      return '完成'
    case 'cancelled':
      return '已取消'
    default:
      return ''
  }
})

const reconWsMessage = computed(() => {
  if (!props.websocketProgress) return ''
  if (props.websocketProgress.pipeline !== 'reconstruction') return ''
  return props.websocketProgress.message
})

const statusTagType = computed(() => {
  switch (state.value.status) {
    case 'COMPLETED':
      return 'success'
    case 'RUNNING':
      return 'primary'
    case 'FAILED':
      return 'danger'
    case 'CANCELLED':
      return 'warning'
    default:
      return 'info'
  }
})

const statusText = computed(() => {
  switch (state.value.status) {
    case 'NOT_STARTED':
      return '未开始'
    case 'RUNNING':
      return '运行中'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失败'
    case 'CANCELLED':
      return '已取消'
    default:
      return state.value.status
  }
})

const stageCards = computed(() => {
  const filesByStage: Record<string, ReconFileInfo | undefined> = {}
  for (const f of state.value.files) {
    if (!filesByStage[f.stage]) {
      filesByStage[f.stage] = f
    }
  }

  const stages: { stage: ReconFileInfo['stage']; title: string }[] = [
    { stage: 'dense', title: '稠密点云' },
    { stage: 'mesh', title: '网格' },
    { stage: 'refine', title: '优化网格' },
    { stage: 'texture', title: '纹理模型' },
  ]

  return stages.map((s) => {
    const file = filesByStage[s.stage]
    let statusText = '未生成'
    let tagType: 'info' | 'primary' | 'success' = 'info'

    if (file) {
      statusText = '已生成'
      tagType = 'success'
    } else if (state.value.status === 'RUNNING') {
      statusText = '处理中'
      tagType = 'primary'
    }

    return {
      stage: s.stage,
      title: s.title,
      file,
      statusText,
      tagType,
    }
  })
})

async function refresh() {
  await blocksStore.fetchReconstructionStatus(props.block.id)
  await blocksStore.fetchReconstructionFiles(props.block.id)
}

async function onStart() {
  try {
    loadingAction.value = true
    await blocksStore.startReconstruction(props.block.id, qualityPreset.value)
    ElMessage.success('重建任务已启动')
    await refresh()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '重建启动失败')
  } finally {
    loadingAction.value = false
  }
}

async function onCancel() {
  try {
    await ElMessageBox.confirm('确定要中止当前重建吗？', '确认中止', {
      type: 'warning',
    })
    loadingAction.value = true
    await blocksStore.cancelReconstruction(props.block.id)
    ElMessage.success('重建已请求中止')
    await refresh()
  } catch {
    // 用户取消
  } finally {
    loadingAction.value = false
  }
}

function openPreview(file: ReconFileInfo) {
  previewFile.value = file
  previewVisible.value = true
}

function formatSize(size: number) {
  if (size > 1024 * 1024 * 1024) {
    return (size / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
  }
  if (size > 1024 * 1024) {
    return (size / (1024 * 1024)).toFixed(1) + ' MB'
  }
  if (size > 1024) {
    return (size / 1024).toFixed(1) + ' KB'
  }
  return size + ' B'
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString()
}

const logText = computed(() => {
  if (logLines.value.length === 0) {
    return '暂无日志'
  }
  return logLines.value.join('\n')
})

async function fetchLog() {
  try {
    const res = await reconstructionApi.logTail(props.block.id, 400)
    logLines.value = res.data.lines
  } catch (e) {
    // 日志获取失败仅在控制台提示，不打断 UI
    console.error(e)
  }
}

function setupLogPolling() {
  if (logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
  if (state.value.status === 'RUNNING') {
    logTimer = window.setInterval(fetchLog, 2000)
  }
}

function disposeLogPolling() {
  if (logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
}

function toggleLog() {
  showLog.value = !showLog.value
}

async function refreshLog() {
  await fetchLog()
}

onMounted(async () => {
  await refresh()
  await fetchLog()
  setupLogPolling()
})

watch(
  () => props.block.id,
  async () => {
    await refresh()
    await fetchLog()
    setupLogPolling()
  },
)

watch(
  () => state.value.status,
  () => {
    setupLogPolling()
  },
)

onUnmounted(() => {
  disposeLogPolling()
})
</script>

<style scoped>
.recon-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.recon-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-label {
  font-size: 13px;
  color: #606266;
}

.status-progress {
  width: 360px;
}

.status-message {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.actions {
  display: flex;
  align-items: center;
}

.stage-row {
  margin-top: 8px;
}

.stage-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-body {
  min-height: 80px;
}

.file-name {
  font-weight: 500;
  margin-bottom: 4px;
  word-break: break-all;
}

.file-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.empty {
  text-align: center;
  color: #c0c4cc;
}

.log-section {
  margin-top: 8px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-actions {
  display: flex;
  gap: 8px;
}

.log-content {
  background: #1a1a2e;
  border-radius: 6px;
  padding: 8px;
}

.log-text {
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #e5eaf3;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-section {
  margin-top: 8px;
}

.error-box {
  max-height: 200px;
  overflow: auto;
  background: #18181c;
  color: #e5eaf3;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
}

.debug-section {
  margin-top: 16px;
}

.debug-section code {
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  font-size: 12px;
}
</style>


