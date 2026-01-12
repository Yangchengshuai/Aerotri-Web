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
          @change="onPresetChange"
        >
          <el-option label="快速 (fast)" value="fast" />
          <el-option label="平衡 (balanced)" value="balanced" />
          <el-option label="高质量 (high)" value="high" />
          <el-option v-if="isCustom" label="自定义 (custom)" value="custom" disabled />
        </el-select>
        <el-button
          v-if="hasRunningVersion"
          type="danger"
          :loading="loadingAction"
          @click="onCancelVersion"
        >
          中止重建
        </el-button>
        <el-button
          v-else
          type="primary"
          :loading="loadingAction"
          :disabled="!canStart"
          @click="onCreateVersion"
        >
          创建新版本
        </el-button>
        <el-button
          v-if="versions.length >= 2"
          type="info"
          plain
          @click="goToCompare"
        >
          对比版本
        </el-button>
      </div>
    </div>

    <!-- Version List Section -->
    <el-card class="version-section">
      <template #header>
        <div class="version-header">
          <span>重建版本历史 ({{ versions.length }})</span>
          <el-button text size="small" @click="refreshVersions" :loading="loadingVersions">
            刷新
          </el-button>
        </div>
      </template>
      <div v-if="versions.length === 0" class="empty-versions">
        <el-text type="info">暂无重建版本，点击"创建新版本"开始第一次重建</el-text>
      </div>
      <el-table v-else :data="versions" size="small" stripe>
        <el-table-column prop="version_index" label="版本" width="70">
          <template #default="{ row }">
            <span class="version-badge">v{{ row.version_index }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="quality_preset" label="预设" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="presetTagType(row.quality_preset)">
              {{ presetLabel(row.quality_preset) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="versionStatusTagType(row.status)">
              {{ versionStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="80">
          <template #default="{ row }">
            {{ Math.round(row.progress) }}%
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'COMPLETED'"
              text
              type="primary"
              size="small"
              @click="previewVersion(row)"
            >
              查看
            </el-button>
            <el-button
              v-if="row.status !== 'RUNNING'"
              text
              type="danger"
              size="small"
              @click="deleteVersion(row)"
            >
              删除
            </el-button>
            <el-button
              v-if="row.status === 'RUNNING'"
              text
              type="warning"
              size="small"
              @click="cancelVersion(row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Advanced Parameters Section -->
    <el-card class="params-section">
      <template #header>
        <div class="params-header">
          <span>高级参数</span>
          <el-button 
            text 
            size="small" 
            @click="showParams = !showParams"
          >
            {{ showParams ? '收起' : '展开' }}
          </el-button>
        </div>
      </template>
      <el-collapse-transition>
        <div v-show="showParams">
          <ReconParamsConfig
            ref="paramsConfigRef"
            :preset="effectivePreset"
            v-model="customParams"
            @custom-changed="onCustomChanged"
          />
        </div>
      </el-collapse-transition>
    </el-card>

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
              <div class="file-name">
                {{ card.file.name }}
                <el-tag v-if="card.file.version_index" type="info" size="small" class="version-tag">
                  v{{ card.file.version_index }}
                </el-tag>
              </div>
              <div class="file-meta">
                <span>{{ formatSize(card.file.size_bytes) }}</span>
                <span>·</span>
                <span>{{ formatTime(card.file.mtime) }}</span>
              </div>
              <!-- Show other versions if available -->
              <div v-if="card.files && card.files.length > 1" class="other-versions">
                <span class="other-versions-label">其他版本:</span>
                <el-tag
                  v-for="f in card.files.slice(1)"
                  :key="f.download_url"
                  type="info"
                  size="small"
                  class="version-link"
                  @click="downloadFile(f)"
                >
                  v{{ f.version_index || '?' }}
                </el-tag>
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
          <code v-if="activeVersion">{{ activeVersion.output_path }} (v{{ activeVersion.version_index }})</code>
          <code v-else-if="block.recon_output_path">{{ block.recon_output_path }} (legacy)</code>
          <code v-else>暂无（尚未重建）</code>
        </el-descriptions-item>
        <el-descriptions-item v-if="versions.length > 0" label="版本数量">
          <code>{{ versions.length }} 个版本</code>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { 
  Block, 
  ReconFileInfo, 
  ReconstructionState, 
  ProgressMessage,
  ReconQualityPreset,
  ReconstructionParams,
  ReconVersion,
} from '@/types'
import { useBlocksStore } from '@/stores/blocks'
import { reconstructionApi, reconVersionApi } from '@/api'
import ReconstructionViewer from './ReconstructionViewer.vue'
import ReconParamsConfig from './ReconParamsConfig.vue'

const props = defineProps<{
  block: Block
  websocketProgress?: ProgressMessage | null
}>()

const router = useRouter()
const blocksStore = useBlocksStore()

const qualityPreset = ref<ReconQualityPreset | 'custom'>('balanced')
const previewVisible = ref(false)
const previewFile = ref<ReconFileInfo | null>(null)
const loadingAction = ref(false)
const logLines = ref<string[]>([])
const showLog = ref(true)
const showParams = ref(false)
const customParams = ref<ReconstructionParams | null>(null)
const isCustom = ref(false)
const paramsConfigRef = ref<InstanceType<typeof ReconParamsConfig> | null>(null)
let logTimer: number | null = null

// Version management state
const versions = ref<ReconVersion[]>([])
const loadingVersions = ref(false)
let versionPollTimer: number | null = null

// Effective preset for the params config (never 'custom')
const effectivePreset = computed<ReconQualityPreset>(() => {
  if (qualityPreset.value === 'custom') {
    return 'balanced'  // Default base for custom
  }
  return qualityPreset.value
})

// Handle preset selection change
function onPresetChange(preset: ReconQualityPreset | 'custom') {
  if (preset !== 'custom') {
    isCustom.value = false
    // Reset params to preset values
    paramsConfigRef.value?.applyPreset(preset)
  }
}

// Handle custom parameter change
function onCustomChanged() {
  isCustom.value = true
  qualityPreset.value = 'custom'
}

// Store-based state (fallback)
const storeState = computed<ReconstructionState>(() =>
  blocksStore.getReconstructionState(props.block.id),
)

// Check if any version is currently running
const hasRunningVersion = computed(() => {
  return versions.value.some(v => v.status === 'RUNNING')
})

// Get the currently running version
const runningVersion = computed(() => {
  return versions.value.find(v => v.status === 'RUNNING')
})

// Get the latest version (highest version_index)
const latestVersion = computed(() => {
  if (versions.value.length === 0) return null
  return versions.value.reduce((latest, v) => 
    v.version_index > latest.version_index ? v : latest
  )
})

// Active version for status display: running version > latest version
const activeVersion = computed(() => {
  return runningVersion.value || latestVersion.value
})

// Computed state based on version list (preferred) or store (fallback)
const state = computed<ReconstructionState>(() => {
  // If we have an active version, derive state from it
  if (activeVersion.value) {
    return {
      status: activeVersion.value.status,
      progress: activeVersion.value.progress,
      currentStage: activeVersion.value.current_stage,
      files: storeState.value.files, // Files still come from store
    }
  }
  // Fallback to store state
  return storeState.value
})

const isRunning = computed(() => state.value.status === 'RUNNING')

const canStart = computed(() => {
  // Can start new version if SfM is completed and no version is running
  return props.block.status === 'completed' && !hasRunningVersion.value
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
  // Group files by stage, collecting all versions
  const filesByStage: Record<string, ReconFileInfo[]> = {}
  for (const f of storeState.value.files) {
    if (!filesByStage[f.stage]) {
      filesByStage[f.stage] = []
    }
    filesByStage[f.stage].push(f)
  }

  const stages: { stage: ReconFileInfo['stage']; title: string }[] = [
    { stage: 'dense', title: '稠密点云' },
    { stage: 'mesh', title: '网格' },
    { stage: 'refine', title: '优化网格' },
    { stage: 'texture', title: '纹理模型' },
  ]

  return stages.map((s) => {
    const files = filesByStage[s.stage] || []
    // Sort by version_index descending (latest first)
    files.sort((a, b) => (b.version_index ?? 0) - (a.version_index ?? 0))
    
    // Use the first (latest) file for display
    const file = files[0] || null
    let statusText = '未生成'
    let tagType: 'info' | 'primary' | 'success' = 'info'

    if (file) {
      // Show version count if multiple versions exist
      if (files.length > 1) {
        statusText = `已生成 (${files.length}个版本)`
      } else if (file.version_index) {
        statusText = `已生成 (v${file.version_index})`
      } else {
        statusText = '已生成'
      }
      tagType = 'success'
    } else if (state.value.status === 'RUNNING') {
      statusText = '处理中'
      tagType = 'primary'
    }

    return {
      stage: s.stage,
      title: s.title,
      file,
      files, // All versions of this stage's files
      statusText,
      tagType,
    }
  })
})

async function refresh() {
  await blocksStore.fetchReconstructionStatus(props.block.id)
  await blocksStore.fetchReconstructionFiles(props.block.id)
}

// Version management functions
async function refreshVersions() {
  try {
    loadingVersions.value = true
    const res = await reconVersionApi.list(props.block.id)
    versions.value = res.data.versions
  } catch (e) {
    console.error('Failed to fetch versions:', e)
  } finally {
    loadingVersions.value = false
  }
}

async function onCreateVersion() {
  try {
    loadingAction.value = true
    const preset = effectivePreset.value
    const params = isCustom.value ? customParams.value : undefined
    
    await reconVersionApi.create(props.block.id, {
      quality_preset: preset,
      custom_params: params || undefined,
    })
    
    ElMessage.success('新版本已创建，重建任务已启动')
    await refreshVersions()
    setupVersionPolling()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建版本失败')
  } finally {
    loadingAction.value = false
  }
}

async function onCancelVersion() {
  const running = runningVersion.value
  if (!running) return
  
  try {
    await ElMessageBox.confirm('确定要中止当前重建吗？', '确认中止', {
      type: 'warning',
    })
    loadingAction.value = true
    await reconVersionApi.cancel(props.block.id, running.id)
    ElMessage.success('重建已请求中止')
    await refreshVersions()
  } catch {
    // User cancelled
  } finally {
    loadingAction.value = false
  }
}

async function cancelVersion(version: ReconVersion) {
  try {
    await ElMessageBox.confirm(`确定要中止版本 v${version.version_index} 的重建吗？`, '确认中止', {
      type: 'warning',
    })
    await reconVersionApi.cancel(props.block.id, version.id)
    ElMessage.success('重建已请求中止')
    await refreshVersions()
  } catch {
    // User cancelled
  }
}

async function deleteVersion(version: ReconVersion) {
  try {
    await ElMessageBox.confirm(
      `确定要删除版本 v${version.version_index} (${version.name}) 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )
    await reconVersionApi.delete(props.block.id, version.id)
    ElMessage.success('版本已删除')
    await refreshVersions()
  } catch {
    // User cancelled
  }
}

function previewVersion(version: ReconVersion) {
  // TODO: Open version preview dialog or navigate to compare view with single version
  ElMessage.info(`查看版本 v${version.version_index} 的功能正在开发中`)
}

function goToCompare() {
  router.push({
    name: 'ReconCompare',
    params: { blockId: props.block.id }
  })
}

// Version status helpers
function versionStatusTagType(status: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  switch (status) {
    case 'COMPLETED': return 'success'
    case 'RUNNING': return ''
    case 'FAILED': return 'danger'
    case 'CANCELLED': return 'warning'
    case 'PENDING': return 'info'
    default: return 'info'
  }
}

function versionStatusText(status: string): string {
  switch (status) {
    case 'COMPLETED': return '已完成'
    case 'RUNNING': return '运行中'
    case 'FAILED': return '失败'
    case 'CANCELLED': return '已取消'
    case 'PENDING': return '等待中'
    default: return status
  }
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

// Version polling for running versions
function setupVersionPolling() {
  disposeVersionPolling()
  if (hasRunningVersion.value) {
    versionPollTimer = window.setInterval(refreshVersions, 3000)
  }
}

function disposeVersionPolling() {
  if (versionPollTimer) {
    clearInterval(versionPollTimer)
    versionPollTimer = null
  }
}

// Legacy reconstruction handlers (for backward compatibility)
async function onStart() {
  await onCreateVersion()
}

async function onCancel() {
  await onCancelVersion()
}

function openPreview(file: ReconFileInfo) {
  previewFile.value = file
  previewVisible.value = true
}

function downloadFile(file: ReconFileInfo) {
  // Open download URL in new tab
  window.open(file.download_url, '_blank')
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
  await refreshVersions()
  await fetchLog()
  setupLogPolling()
  setupVersionPolling()
})

watch(
  () => props.block.id,
  async () => {
    await refresh()
    await refreshVersions()
    await fetchLog()
    setupLogPolling()
    setupVersionPolling()
  },
)

watch(
  () => state.value.status,
  () => {
    setupLogPolling()
  },
)

watch(
  () => hasRunningVersion.value,
  () => {
    setupVersionPolling()
  },
)

onUnmounted(() => {
  disposeLogPolling()
  disposeVersionPolling()
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

.params-section {
  margin-top: 12px;
}

.params-header {
  display: flex;
  justify-content: space-between;
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

.version-tag {
  margin-left: 8px;
  vertical-align: middle;
}

.other-versions {
  margin-bottom: 8px;
  font-size: 12px;
}

.other-versions-label {
  color: #909399;
  margin-right: 4px;
}

.version-link {
  cursor: pointer;
  margin-right: 4px;
}

.version-link:hover {
  opacity: 0.8;
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

.version-section {
  margin-top: 12px;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-versions {
  text-align: center;
  padding: 24px;
}

.version-badge {
  display: inline-block;
  background: #ecf5ff;
  color: #409eff;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 12px;
}
</style>


