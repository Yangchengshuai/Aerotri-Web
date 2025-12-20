<template>
  <el-card class="panel-card">
    <template #header>
      <div class="card-header">
        <span>分区状态</span>
        <el-button 
          type="primary" 
          link 
          @click="refresh"
          :loading="loading"
        >
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </template>

    <div v-if="loading && !partitions.length" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="partitions.length === 0" class="empty-container">
      <el-empty description="暂无分区数据" />
    </div>

    <el-table
      v-else
      :data="partitions"
      stripe
      style="width: 100%"
      :default-sort="{ prop: 'index', order: 'ascending' }"
    >
      <el-table-column prop="index" label="分区" width="80" sortable>
        <template #default="{ row }">
          <el-tag>{{ row.name }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag 
            :type="getStatusType(row.status)"
            effect="dark"
          >
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="image_count" label="图像数" width="100" />
      
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }">
          <el-progress 
            v-if="row.progress !== null && row.progress !== undefined"
            :percentage="Math.round(row.progress)"
            :status="row.status === 'FAILED' ? 'exception' : undefined"
          />
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'COMPLETED'"
            type="primary"
            link
            size="small"
            @click="viewPartition(row.index)"
          >
            查看结果
          </el-button>
          <el-button
            v-if="row.error_message"
            type="danger"
            link
            size="small"
            @click="showError(row.error_message)"
          >
            查看错误
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { partitionApi } from '@/api'

interface Partition {
  id?: string
  index: number
  name: string
  image_start_name: string | null
  image_end_name: string | null
  image_count: number
  overlap_with_prev: number
  overlap_with_next: number
  status: string | null
  progress: number | null
  error_message: string | null
}

const props = defineProps<{
  blockId: string
}>()

const partitions = ref<Partition[]>([])
const loading = ref(false)

function getStatusType(status: string | null): string {
  if (!status) return 'info'
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return 'success'
    case 'RUNNING':
      return 'warning'
    case 'FAILED':
      return 'danger'
    default:
      return 'info'
  }
}

function getStatusText(status: string | null): string {
  if (!status) return '未知'
  switch (status.toUpperCase()) {
    case 'COMPLETED':
      return '已完成'
    case 'RUNNING':
      return '运行中'
    case 'FAILED':
      return '失败'
    default:
      return status
  }
}

function viewPartition(index: number) {
  // TODO: Navigate to partition detail view or show in modal
  ElMessage.info(`查看分区 ${index} 的结果`)
}

function showError(errorMessage: string) {
  ElMessage.error({
    message: errorMessage,
    duration: 5000,
    showClose: true,
  })
}

async function refresh() {
  loading.value = true
  try {
    const response = await partitionApi.getStatus(props.blockId)
    partitions.value = response.data.partitions || []
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '获取分区状态失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container,
.empty-container {
  padding: 20px;
  text-align: center;
}
</style>
