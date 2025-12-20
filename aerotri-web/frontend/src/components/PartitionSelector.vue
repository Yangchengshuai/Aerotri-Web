<template>
  <div class="partition-selector">
    <el-select
      v-model="selectedPartitionIndex"
      placeholder="选择分区"
      @change="handlePartitionChange"
      :disabled="loading || partitions.length === 0"
      style="width: 200px"
    >
      <el-option
        v-for="partition in completedPartitions"
        :key="partition.index"
        :label="partition.name"
        :value="partition.index"
      >
        <div class="partition-option">
          <span>{{ partition.name }}</span>
          <el-tag size="small" type="success" style="margin-left: 8px">
            {{ partition.statistics?.num_registered_images || 0 }} 相机
          </el-tag>
        </div>
      </el-option>
    </el-select>
    
    <el-tooltip content="刷新分区列表" placement="top">
      <el-button
        :icon="Refresh"
        circle
        size="small"
        @click="refresh"
        :loading="loading"
        style="margin-left: 8px"
      />
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { partitionApi } from '@/api'

interface Partition {
  id?: string
  index: number
  name: string
  status: string | null
  statistics?: {
    num_registered_images?: number
    num_points3d?: number
    num_observations?: number
    mean_reprojection_error?: number
    mean_track_length?: number
  } | null
}

const props = defineProps<{
  blockId: string
  modelValue: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  'change': [partitionIndex: number | null]
}>()

const partitions = ref<Partition[]>([])
const loading = ref(false)
const selectedPartitionIndex = ref<number | null>(props.modelValue)

const completedPartitions = computed(() => {
  return partitions.value.filter(p => p.status === 'COMPLETED')
})

watch(() => props.modelValue, (newValue) => {
  selectedPartitionIndex.value = newValue
})

function handlePartitionChange(value: number | null) {
  emit('update:modelValue', value)
  emit('change', value)
}

async function refresh() {
  loading.value = true
  try {
    const response = await partitionApi.getStatus(props.blockId)
    partitions.value = response.data.partitions || []
    
    // If no partition is selected and there are completed partitions, select the first one
    if (selectedPartitionIndex.value === null && completedPartitions.value.length > 0) {
      const firstPartition = completedPartitions.value[0]
      handlePartitionChange(firstPartition.index)
    }
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
.partition-selector {
  display: flex;
  align-items: center;
}

.partition-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>

