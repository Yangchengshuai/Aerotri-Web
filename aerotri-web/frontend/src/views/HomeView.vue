<template>
  <div class="home-view">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <h1>AeroTri Web</h1>
        <span class="subtitle">空中三角测量工具</span>
      </div>
      <div class="header-right">
        <!-- 运行状态指示器 -->
        <el-tag 
          :type="queueStore.runningCount > 0 ? 'success' : 'info'" 
          size="large"
          class="running-indicator"
        >
          运行中 {{ queueStore.runningCount }}/{{ queueStore.maxConcurrent }}
        </el-tag>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建 Block
        </el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main-content">
      <!-- Queue Section -->
      <div v-if="queueStore.items.length > 0" class="queue-section">
        <div class="section-header">
          <h2>
            <el-icon><Clock /></el-icon>
            排队任务
            <el-tag size="small" type="warning">{{ queueStore.items.length }}</el-tag>
          </h2>
          <el-button text size="small" @click="openConfigDialog">
            <el-icon><Setting /></el-icon>
            并发配置
          </el-button>
        </div>
        <div class="queue-list">
          <div 
            v-for="item in queueStore.sortedItems" 
            :key="item.id" 
            class="queue-item"
          >
            <div class="queue-item__position">{{ item.queue_position }}</div>
            <div class="queue-item__info">
              <span class="queue-item__name">{{ item.name }}</span>
              <div class="queue-item__meta">
                <el-tag size="small" type="info">{{ item.algorithm }}</el-tag>
                <span class="queue-item__time">{{ formatQueuedTime(item.queued_at) }}</span>
              </div>
            </div>
            <div class="queue-item__actions">
              <el-button 
                v-if="item.queue_position > 1"
                size="small" 
                @click="handleMoveToTop(item.id)"
              >
                置顶
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                plain
                @click="handleDequeue(item.id)"
              >
                移除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Block List -->
      <div class="block-list">
        <!-- Selection Toolbar -->
        <div v-if="selectionMode" class="selection-toolbar">
          <div class="selection-info">
            <el-checkbox
              v-model="selectAll"
              :indeterminate="isIndeterminate"
              @change="handleSelectAll"
            >
              全选
            </el-checkbox>
            <span class="selected-count">
              已选择 {{ selectedBlocks.length }} 个 Block
            </span>
          </div>
          <div class="selection-actions">
            <el-button
              type="primary"
              :disabled="selectedBlocks.length !== 2"
              @click="goToCompare"
            >
              <el-icon><TrendCharts /></el-icon>
              对比选中 Block ({{ selectedBlocks.length }}/2)
            </el-button>
            <el-button @click="cancelSelection">
              取消
            </el-button>
          </div>
        </div>

        <div v-else class="section-header-bar">
          <h3>Blocks ({{ blocksStore.blocks.length }})</h3>
          <el-button text @click="selectionMode = true">
            <el-icon><Grid /></el-icon>
            批量选择
          </el-button>
        </div>

        <el-card v-if="blocksStore.loading" class="loading-card">
          <el-skeleton :rows="5" animated />
        </el-card>
        
        <el-alert
          v-else-if="blocksStore.error"
          :title="blocksStore.error"
          type="error"
          :closable="false"
          show-icon
        />
        
        <el-empty 
          v-else-if="blocksStore.blocks.length === 0"
          description="暂无 Block，点击上方按钮创建"
        />
        
        <div v-else class="block-grid">
          <div
            v-for="block in blocksStore.sortedBlocks"
            :key="block.id"
            class="block-grid-item"
            :class="{ 'is-selected': isBlockSelected(block.id) }"
          >
            <el-checkbox
              v-if="selectionMode"
              v-model="selectedBlocksSet"
              :value="block.id"
              class="block-checkbox"
              @click.stop
            />
            <BlockCard
              :block="block"
              @click="handleBlockClick(block)"
              @delete="handleDelete(block)"
            />
          </div>
        </div>
      </div>
    </el-main>

    <!-- Create Block Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建 Block"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="formData.name" placeholder="输入 Block 名称" />
        </el-form-item>
        
        <el-form-item label="图像目录" prop="image_path">
          <el-input v-model="formData.image_path" placeholder="输入图像目录路径">
            <template #append>
              <el-button @click="browseDirectory">浏览</el-button>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item label="算法" prop="algorithm">
          <el-radio-group v-model="formData.algorithm">
            <el-radio value="glomap">GLOMAP (全局式)</el-radio>
            <el-radio value="colmap">COLMAP (增量式)</el-radio>
            <el-radio value="instantsfm">InstantSfM (快速全局式)</el-radio>
            <el-radio value="openmvg_global">openMVG (全局式)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showDirectoryDialog"
      title="选择图像目录"
      width="640px"
      destroy-on-close
    >
      <div class="dir-browser">
        <div class="dir-browser__header">
          <span class="current-path">{{ currentDir || '请选择目录' }}</span>
          <el-button text size="small" :disabled="!parentDir" @click="goParent">上一级</el-button>
        </div>
        <el-skeleton v-if="directoryLoading" :rows="4" animated />
        <el-empty v-else-if="directoryEntries.length === 0" description="没有可用的子目录" />
        <el-scrollbar v-else class="dir-list">
          <div
            v-for="entry in directoryEntries"
            :key="entry.path"
            class="dir-item"
          >
            <div class="dir-item__info" @click="openDirectory(entry.path)">
              <el-icon><Folder /></el-icon>
              <span class="dir-name">{{ entry.name }}</span>
              <div class="dir-tags">
                <el-tag v-if="entry.has_images" size="small" type="success" effect="plain">含图像</el-tag>
                <el-tag v-if="entry.has_subdirs" size="small" effect="plain">有子目录</el-tag>
              </div>
            </div>
            <el-button size="small" @click="selectDirectory(entry.path)">选择</el-button>
          </div>
        </el-scrollbar>
      </div>
    </el-dialog>

    <!-- Queue Config Dialog -->
    <el-dialog
      v-model="showConfigDialog"
      title="队列配置"
      width="400px"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item label="最大并发数">
          <el-input-number 
            v-model="newMaxConcurrent" 
            :min="1" 
            :max="10"
          />
        </el-form-item>
        <el-form-item>
          <span class="config-hint">当前正在运行 {{ queueStore.runningCount }} 个任务</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Folder, Clock, Setting, Grid, TrendCharts } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import { useQueueStore } from '@/stores/queue'
import type { Block, DirectoryEntry } from '@/types'
import { filesystemApi } from '@/api'
import BlockCard from '@/components/BlockCard.vue'

const router = useRouter()
const blocksStore = useBlocksStore()
const queueStore = useQueueStore()

const showCreateDialog = ref(false)
const showConfigDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()
const newMaxConcurrent = ref(2)

const showDirectoryDialog = ref(false)
const directoryLoading = ref(false)
const directoryEntries = ref<DirectoryEntry[]>([])
const currentDir = ref('')
const parentDir = ref<string | null>(null)

const formData = reactive({
  name: '',
  image_path: '',
  algorithm: 'glomap',
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入 Block 名称', trigger: 'blur' },
    { min: 1, max: 255, message: '名称长度在 1 到 255 个字符之间', trigger: 'blur' },
  ],
  image_path: [
    { required: true, message: '请选择图像路径', trigger: 'change' },
  ],
  algorithm: [
    { required: true, message: '请选择算法', trigger: 'change' },
  ],
}

// Batch selection state
const selectionMode = ref(false)
const selectedBlocksSet = ref<string[]>([])

const selectedBlocks = computed(() => {
  return selectedBlocksSet.value.map(id =>
    blocksStore.blocks.find(b => b.id === id)
  ).filter(Boolean) as Block[]
})

const selectAll = computed({
  get: () => selectedBlocksSet.value.length === blocksStore.blocks.length && blocksStore.blocks.length > 0,
  set: (value: boolean) => {
    if (value) {
      selectedBlocksSet.value = blocksStore.blocks.map(b => b.id)
    } else {
      selectedBlocksSet.value = []
    }
  }
})

const isIndeterminate = computed(() => {
  const selectedCount = selectedBlocksSet.value.length
  const totalCount = blocksStore.blocks.length
  return selectedCount > 0 && selectedCount < totalCount
})

// Selection functions
function isBlockSelected(blockId: string): boolean {
  return selectedBlocksSet.value.includes(blockId)
}

function handleSelectAll(value: boolean) {
  // Computed setter handles this
}

function handleBlockClick(block: Block) {
  if (selectionMode.value) {
    // Toggle selection
    const index = selectedBlocksSet.value.indexOf(block.id)
    if (index > -1) {
      selectedBlocksSet.value.splice(index, 1)
    } else {
      selectedBlocksSet.value.push(block.id)
    }
  } else {
    // Normal navigation
    goToBlock(block.id)
  }
}

function cancelSelection() {
  selectionMode.value = false
  selectedBlocksSet.value = []
}

function goToCompare() {
  if (selectedBlocks.value.length === 2) {
    router.push({
      name: 'Compare',
      query: {
        left: selectedBlocks.value[0].id,
        right: selectedBlocks.value[1].id
      }
    })
  }
}

let queuePollTimer: number | null = null

onMounted(async () => {
  await Promise.all([
    blocksStore.fetchBlocks(),
    queueStore.fetchQueue(),
  ])
  // Poll queue every 5 seconds
  queuePollTimer = window.setInterval(() => {
    queueStore.fetchQueue()
  }, 5000)
})

onUnmounted(() => {
  if (queuePollTimer) {
    clearInterval(queuePollTimer)
    queuePollTimer = null
  }
})

function goToBlock(id: string) {
  router.push({ name: 'BlockDetail', params: { id } })
}

async function handleCreate() {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  creating.value = true
  try {
    const block = await blocksStore.createBlock(formData)
    ElMessage.success('Block 创建成功')
    showCreateDialog.value = false
    
    // Reset form
    formData.name = ''
    formData.image_path = ''
    formData.algorithm = 'glomap'
    
    // Navigate to new block
    goToBlock(block.id)
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleDelete(block: Block) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 Block "${block.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    await blocksStore.deleteBlock(block.id)
    ElMessage.success('删除成功')
  } catch {
    // User cancelled or error
  }
}

async function browseDirectory() {
  showDirectoryDialog.value = true
  await loadDirectories()
}

async function loadDirectories(path?: string) {
  directoryLoading.value = true
  try {
    const resp = await filesystemApi.listDirs(path)
    directoryEntries.value = resp.data.entries
    currentDir.value = resp.data.current
    parentDir.value = resp.data.parent
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '目录加载失败')
  } finally {
    directoryLoading.value = false
  }
}

function openDirectory(path: string) {
  loadDirectories(path)
}

function goParent() {
  if (parentDir.value) {
    loadDirectories(parentDir.value)
  }
}

function selectDirectory(path: string) {
  formData.image_path = path
  showDirectoryDialog.value = false
}

// Queue operations
async function handleMoveToTop(blockId: string) {
  try {
    await queueStore.moveToTop(blockId)
    ElMessage.success('已置顶')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '置顶失败')
  }
}

async function handleDequeue(blockId: string) {
  try {
    await ElMessageBox.confirm('确定要从队列中移除此任务吗？', '确认移除', { type: 'warning' })
    await queueStore.dequeue(blockId)
    ElMessage.success('已从队列移除')
  } catch {
    // User cancelled
  }
}

async function handleUpdateConfig() {
  try {
    await queueStore.updateConfig(newMaxConcurrent.value)
    showConfigDialog.value = false
    ElMessage.success('配置已更新')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}

function openConfigDialog() {
  newMaxConcurrent.value = queueStore.maxConcurrent
  showConfigDialog.value = true
}

function formatQueuedTime(isoTime: string): string {
  try {
    const date = new Date(isoTime)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return isoTime
  }
}
</script>

<style scoped>
.home-view {
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
  align-items: baseline;
  gap: 16px;
}

.header-left h1 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.subtitle {
  color: #909399;
  font-size: 14px;
}

.main-content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}

.block-list {
  max-width: 1400px;
  margin: 0 auto;
}

.loading-card {
  max-width: 600px;
  margin: 0 auto;
}

.block-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.dir-browser {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dir-browser__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #606266;
}

.current-path {
  word-break: break-all;
}

.dir-list {
  max-height: 320px;
}

.dir-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  margin-bottom: 10px;
  transition: all 0.15s ease;
}

.dir-item:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.dir-item__info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.dir-name {
  font-weight: 500;
  color: #303133;
}

.dir-tags {
  display: flex;
  gap: 6px;
}

/* Queue Section Styles */
.running-indicator {
  margin-right: 12px;
}

.queue-section {
  max-width: 1400px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #fff7e6 0%, #fffbe6 100%);
  border: 1px solid #ffd666;
  border-radius: 8px;
  padding: 16px 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: #d48806;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  border-radius: 6px;
  padding: 10px 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.queue-item__position {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #fa8c16;
  color: white;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.queue-item__info {
  flex: 1;
  min-width: 0;
}

.queue-item__name {
  font-weight: 500;
  color: #303133;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.queue-item__time {
  color: #909399;
}

.queue-item__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.config-hint {
  color: #909399;
  font-size: 13px;
}

/* Selection Toolbar */
.selection-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 16px;
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selected-count {
  font-size: 14px;
  color: #606266;
}

.selection-actions {
  display: flex;
  gap: 8px;
}

.section-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header-bar h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

/* Block Grid Item with Checkbox */
.block-grid-item {
  position: relative;
}

.block-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  padding: 4px;
  background: white;
  border-radius: 4px;
}

.block-grid-item.is-selected {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
  border-radius: 4px;
}
</style>
