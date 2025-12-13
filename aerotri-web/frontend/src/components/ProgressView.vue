<template>
  <div class="progress-view">
    <!-- Stage Indicator -->
    <div class="stage-indicator">
      <el-steps :active="currentStageIndex" finish-status="success" align-center>
        <el-step v-for="stage in stages" :key="stage.key" :title="stage.label">
          <template #description>
            <span v-if="stageTimes[stage.key]">
              {{ formatTime(stageTimes[stage.key]) }}
            </span>
          </template>
        </el-step>
      </el-steps>
    </div>

    <!-- Current Progress -->
    <el-card class="progress-card">
      <template #header>
        <div class="card-header">
          <span>当前进度</span>
          <el-tag :type="statusType" size="small">{{ statusText }}</el-tag>
        </div>
      </template>

      <div class="current-progress">
        <div class="stage-name">{{ currentStageName }}</div>
        <el-progress
          :percentage="progressPercentage"
          :stroke-width="20"
          :text-inside="true"
          :status="progressStatus"
        />
        <div class="progress-info" v-if="websocketProgress">
          {{ websocketProgress.message }}
        </div>
      </div>

      <!-- Time Stats -->
      <div class="time-stats" v-if="block.started_at">
        <div class="stat">
          <span class="label">开始时间</span>
          <span class="value">{{ formatDate(block.started_at) }}</span>
        </div>
        <div class="stat">
          <span class="label">已运行</span>
          <span class="value">{{ elapsedTime }}</span>
        </div>
        <div class="stat" v-if="block.completed_at">
          <span class="label">完成时间</span>
          <span class="value">{{ formatDate(block.completed_at) }}</span>
        </div>
      </div>
    </el-card>

    <!-- Log Output -->
    <el-card class="log-card">
      <template #header>
        <div class="card-header">
          <span>运行日志</span>
          <el-button text @click="toggleLog">
            {{ showLog ? '收起' : '展开' }}
          </el-button>
        </div>
      </template>
      
      <el-collapse-transition>
        <div v-show="showLog" class="log-content">
          <el-scrollbar ref="logScrollbar" height="300px">
            <pre class="log-text">{{ logText }}</pre>
          </el-scrollbar>
        </div>
      </el-collapse-transition>
    </el-card>

    <!-- Error Display -->
    <el-alert
      v-if="block.status === 'failed' && block.error_message"
      type="error"
      :title="block.error_message"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import type { Block, ProgressMessage } from '@/types'
import { taskApi } from '@/api'

const props = defineProps<{
  block: Block
  websocketProgress: ProgressMessage | null
}>()

const stages = [
  { key: 'feature_extraction', label: '特征提取' },
  { key: 'matching', label: '特征匹配' },
  { key: 'mapping', label: '重建' },
  { key: 'completed', label: '完成' },
]

const showLog = ref(true)
const logTail = ref<string[]>([])
const stageTimes = ref<Record<string, number>>({})

const currentStageIndex = computed(() => {
  const stage = props.block.current_stage
  if (!stage) return -1
  const index = stages.findIndex(s => s.key === stage)
  return index >= 0 ? index : 0
})

const currentStageName = computed(() => {
  const stage = stages.find(s => s.key === props.block.current_stage)
  return stage?.label || props.block.current_stage || '准备中'
})

const progressPercentage = computed(() => {
  if (props.websocketProgress) {
    return Math.round(props.websocketProgress.progress)
  }
  return Math.round(props.block.progress || 0)
})

const statusType = computed(() => {
  switch (props.block.status) {
    case 'completed': return 'success'
    case 'running': return ''
    case 'failed': return 'danger'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (props.block.status) {
    case 'created': return '待处理'
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return props.block.status
  }
})

const progressStatus = computed(() => {
  if (props.block.status === 'completed') return 'success'
  if (props.block.status === 'failed') return 'exception'
  return ''
})

const logText = computed(() => {
  return logTail.value.join('\n') || '暂无日志'
})

function parseServerDate(dateStr: string): Date {
  // Backend stores naive datetime in UTC (no timezone suffix).
  // JS will treat it as local time -> causes +8h elapsed in China.
  // Fix by appending 'Z' when timezone is absent.
  const hasTz = /[zZ]$|[+-]\d{2}:\d{2}$/.test(dateStr)
  return new Date(hasTz ? dateStr : `${dateStr}Z`)
}

const elapsedTime = computed(() => {
  if (!props.block.started_at) return '-'
  
  const start = parseServerDate(props.block.started_at).getTime()
  const end = props.block.completed_at 
    ? parseServerDate(props.block.completed_at).getTime()
    : Date.now()
  
  return formatTime((end - start) / 1000)
})

// Fetch log tail periodically when running
let logTimer: number | null = null

async function fetchLog() {
  try {
    const response = await taskApi.status(props.block.id)
    if (response.data.log_tail) {
      logTail.value = response.data.log_tail
    }
    if (response.data.stage_times) {
      stageTimes.value = response.data.stage_times
    }
  } catch {
    // Ignore errors
  }
}

onMounted(() => {
  fetchLog()
  if (props.block.status === 'running') {
    logTimer = window.setInterval(fetchLog, 2000)
  }
})

onUnmounted(() => {
  if (logTimer) {
    clearInterval(logTimer)
  }
})

watch(() => props.block.status, (status) => {
  if (status === 'running' && !logTimer) {
    logTimer = window.setInterval(fetchLog, 2000)
  } else if (status !== 'running' && logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
})

// Update stage times from statistics when completed
watch(() => props.block.statistics, (stats) => {
  if (stats?.stage_times) {
    stageTimes.value = stats.stage_times
  }
}, { immediate: true })

function toggleLog() {
  showLog.value = !showLog.value
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

function formatDate(dateStr: string): string {
  return parseServerDate(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.progress-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}

.stage-indicator {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.progress-card,
.log-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.current-progress {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.progress-info {
  font-size: 13px;
  color: #909399;
}

.time-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.time-stats .stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.time-stats .label {
  font-size: 12px;
  color: #909399;
}

.time-stats .value {
  font-size: 14px;
  font-weight: 500;
}

.log-content {
  background: #1a1a2e;
  border-radius: 6px;
  padding: 12px;
}

.log-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #e0e0e0;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
