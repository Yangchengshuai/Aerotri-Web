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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useBlocksStore } from '@/stores/blocks'
import type { Block } from '@/types'
import BlockCard from '@/components/BlockCard.vue'

const router = useRouter()
const blocksStore = useBlocksStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()

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

function browseDirectory() {
  // In a real app, this would open a directory picker
  // For now, just set a default test path
  formData.image_path = '/root/data/city1-CQ02-441-bagcp-riggcp-adj - export'
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
</style>
