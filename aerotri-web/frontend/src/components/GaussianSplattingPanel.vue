<template>
  <div class="gs-panel" v-if="block">
    <div class="gs-header">
      <div class="status">
        <div class="status-line">
          <span>3DGS 状态：</span>
          <el-tag :type="statusTagType">{{ statusText }}</el-tag>
          <span v-if="currentStageLabel" class="stage-label">{{ currentStageLabel }}</span>
        </div>
        <div class="status-progress">
          <el-progress
            :percentage="Math.round(state.progress)"
            :stroke-width="18"
            :text-inside="true"
          />
        </div>
      </div>

      <div class="actions">
        <div class="params">
          <el-input-number v-model="params.iterations" :min="1" :step="1000" size="small" />
          <span class="param-label">iters</span>

          <el-input-number v-model="params.resolution" :min="1" :max="8" size="small" />
          <span class="param-label">res</span>

          <el-select v-model="params.data_device" size="small" style="width: 90px">
            <el-option label="cpu" value="cpu" />
            <el-option label="cuda" value="cuda" />
          </el-select>

          <el-input-number v-model="params.sh_degree" :min="0" :max="3" size="small" />
          <span class="param-label">sh</span>
        </div>

        <div class="gpu">
          <GPUSelector v-model="gpuIndex" />
        </div>

        <div class="buttons">
          <el-button
            v-if="isRunning"
            type="danger"
            :loading="loadingAction"
            @click="onCancel"
          >
            中止训练
          </el-button>
          <el-button
            v-else
            type="primary"
            :loading="loadingAction"
            :disabled="!canStart"
            @click="onStart"
          >
            开始训练
          </el-button>
        </div>
      </div>
    </div>

    <el-card class="files-card">
      <template #header>
        <div class="card-header">
          <span>训练产物</span>
          <el-button text size="small" @click="refreshAll">刷新</el-button>
        </div>
      </template>

      <el-table :data="state.files" size="small" style="width: 100%">
        <el-table-column prop="name" label="文件" min-width="240" />
        <el-table-column prop="type" label="类型" width="110" />
        <el-table-column prop="size_bytes" label="大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.size_bytes) }}
          </template>
        </el-table-column>
        <el-table-column prop="mtime" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.mtime) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              v-if="row.preview_supported"
              type="primary"
              text
              size="small"
              @click="openPreview(row)"
            >
              预览
            </el-button>
            <el-button type="primary" text size="small" :href="row.download_url" target="_blank">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="state.files.length === 0" class="empty">
        <el-text type="info">尚未生成输出</el-text>
      </div>
    </el-card>

    <div class="log-section">
      <el-card>
        <template #header>
          <div class="log-header">
            <span>训练日志</span>
            <div class="log-actions">
              <el-button text size="small" @click="toggleLog">
                {{ showLog ? '收起' : '展开' }}
              </el-button>
              <el-button text size="small" @click="refreshLog">手动刷新</el-button>
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

    <div class="error-section" v-if="block.gs_error_message">
      <h4>最近错误</h4>
      <pre class="error-box">{{ block.gs_error_message }}</pre>
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
        <el-descriptions-item label="3DGS 输出目录">
          <code>{{ block.gs_output_path || '暂无（尚未训练）' }}</code>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <el-dialog v-model="previewVisible" title="3DGS 预览" width="80%" top="3vh" destroy-on-close>
      <div class="preview-wrap">
        <iframe v-if="previewUrl" class="preview-iframe" :src="previewUrl" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Block, GSFileInfo, GSState } from '@/types'
import { gsApi } from '@/api'
import GPUSelector from './GPUSelector.vue'

const props = defineProps<{
  block: Block
}>()

const gpuIndex = ref(0)
const loadingAction = ref(false)
const showLog = ref(true)
const logLines = ref<string[]>([])
let logTimer: number | null = null
let statusTimer: number | null = null

const params = ref({
  iterations: 7000,
  resolution: 2,
  data_device: 'cpu' as 'cpu' | 'cuda',
  sh_degree: 3,
})

const state = ref<GSState>({
  status: (props.block.gs_status as GSState['status']) ?? 'NOT_STARTED',
  progress: props.block.gs_progress ?? 0,
  currentStage: props.block.gs_current_stage ?? null,
  files: [],
})

const isRunning = computed(() => state.value.status === 'RUNNING')

const canStart = computed(() => {
  return ['NOT_STARTED', 'FAILED', 'CANCELLED', 'COMPLETED'].includes(state.value.status)
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
      return '训练中'
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

const currentStageLabel = computed(() => {
  switch (state.value.currentStage) {
    case 'dataset_prepare':
      return '准备数据集'
    case 'training':
      return '训练'
    case 'completed':
      return '完成'
    case 'failed':
      return '失败'
    case 'cancelled':
      return '已取消'
    default:
      return ''
  }
})

const logText = computed(() => logLines.value.join('\n') || '暂无日志')

async function fetchStatus() {
  try {
    const res = await gsApi.status(props.block.id)
    const d = res.data
    state.value.status = (d.gs_status as GSState['status']) ?? 'NOT_STARTED'
    state.value.progress = d.gs_progress ?? 0
    state.value.currentStage = d.gs_current_stage ?? null
  } catch {
    // ignore
  }
}

async function fetchFiles() {
  try {
    const res = await gsApi.files(props.block.id)
    state.value.files = res.data.files
  } catch {
    // ignore
  }
}

async function fetchLog() {
  try {
    const res = await gsApi.logTail(props.block.id, 200)
    logLines.value = res.data.lines || []
  } catch {
    // ignore
  }
}

async function refreshAll() {
  await Promise.all([fetchStatus(), fetchFiles(), fetchLog()])
}

function startPolling() {
  if (!statusTimer) statusTimer = window.setInterval(fetchStatus, 2000)
  if (!logTimer) logTimer = window.setInterval(fetchLog, 2000)
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

async function onStart() {
  try {
    loadingAction.value = true
    await gsApi.train(props.block.id, {
      gpu_index: gpuIndex.value,
      train_params: { ...params.value },
    })
    await refreshAll()
    startPolling()
    ElMessage.success('已启动 3DGS 训练')
  } catch (e) {
    console.error(e)
    ElMessage.error('启动 3DGS 训练失败')
  } finally {
    loadingAction.value = false
  }
}

async function onCancel() {
  try {
    await ElMessageBox.confirm('确定要中止 3DGS 训练吗？', '提示', { type: 'warning' })
    loadingAction.value = true
    await gsApi.cancel(props.block.id)
    await refreshAll()
    stopPolling()
    ElMessage.success('已中止训练')
  } catch {
    // ignore
  } finally {
    loadingAction.value = false
  }
}

function toggleLog() {
  showLog.value = !showLog.value
}

async function refreshLog() {
  await fetchLog()
}

function formatSize(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

const previewVisible = ref(false)
const previewUrl = ref<string | null>(null)

function openPreview(file: GSFileInfo) {
  // Visionary 同域静态页面（将在 M2-viewer-iframe 中落地）
  const plyUrl = file.download_url
  previewUrl.value = `/visionary/index.html?ply_url=${encodeURIComponent(plyUrl)}`
  previewVisible.value = true
}

onMounted(async () => {
  await refreshAll()
  if (state.value.status === 'RUNNING') startPolling()
})

onUnmounted(() => {
  stopPolling()
})

watch(
  () => state.value.status,
  (s) => {
    if (s === 'RUNNING') startPolling()
    else stopPolling()
  },
)
</script>

<style scoped>
.gs-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}

.status {
  flex: 1;
}

.status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.stage-label {
  color: #909399;
  font-size: 12px;
}

.actions {
  width: 520px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.params {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.param-label {
  font-size: 12px;
  color: #909399;
  margin-right: 8px;
}

.gpu {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
}

.buttons {
  display: flex;
  justify-content: flex-end;
}

.files-card {
  margin-top: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty {
  padding: 12px 0;
}

.log-section {
  margin-top: 12px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-actions {
  display: flex;
  gap: 6px;
}

.log-text {
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.error-section {
  margin-top: 12px;
}

.error-box {
  background: #1f1f1f;
  color: #f5f5f5;
  padding: 10px;
  border-radius: 6px;
  overflow: auto;
}

.debug-section {
  margin-top: 12px;
}

.preview-wrap {
  height: 75vh;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: 0;
}
</style>


