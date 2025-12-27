<template>
  <div class="home-view">
    <!-- Header -->
    <el-header class="header">
      <div class="header-left">
        <h1>AeroTri Web</h1>
        <span class="subtitle">空中三角测量工具</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建 Block
        </el-button>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main-content">
      <!-- Block List -->
      <div class="block-list">
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
          <BlockCard
            v-for="block in blocksStore.sortedBlocks"
            :key="block.id"
            :block="block"
            @click="goToBlock(block.id)"
            @delete="handleDelete(block)"
          />
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
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="匹配方法" prop="matching_method">
          <el-select v-model="formData.matching_method" style="width: 100%">
            <el-option label="序列匹配 (Sequential)" value="sequential" />
            <el-option label="穷举匹配 (Exhaustive)" value="exhaustive" />
            <el-option label="词汇树匹配 (Vocab Tree)" value="vocab_tree" />
          </el-select>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Folder } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import type { Block, DirectoryEntry } from '@/types'
import { filesystemApi } from '@/api'
import BlockCard from '@/components/BlockCard.vue'

const router = useRouter()
const blocksStore = useBlocksStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()

const showDirectoryDialog = ref(false)
const directoryLoading = ref(false)
const directoryEntries = ref<DirectoryEntry[]>([])
const currentDir = ref('')
const parentDir = ref<string | null>(null)

const formData = reactive({
  name: '',
  image_path: '',
  algorithm: 'glomap',
  matching_method: 'sequential',
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入 Block 名称', trigger: 'blur' },
    { min: 1, max: 255, message: '名称长度在 1 到 255 个字符之间', trigger: 'blur' },
  ],
  image_path: [
    { required: true, message: '请输入图像目录路径', trigger: 'blur' },
  ],
}

onMounted(async () => {
  await blocksStore.fetchBlocks()
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
    formData.matching_method = 'sequential'
    
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
</style>
