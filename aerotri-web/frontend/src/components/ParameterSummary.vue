<template>
  <div class="parameter-summary">
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="算法">
        {{ block.algorithm === 'glomap' ? 'GLOMAP (全局式)' : 'COLMAP (增量式)' }}
      </el-descriptions-item>
      <el-descriptions-item label="匹配方法">
        {{ matchingMethodText }}
      </el-descriptions-item>
      <el-descriptions-item label="GPU加速">
        {{ gpuEnabled ? '启用' : '禁用' }}
      </el-descriptions-item>
      <el-descriptions-item label="最大图像尺寸">
        {{ block.feature_params?.max_image_size || 2000 }}
      </el-descriptions-item>
      <el-descriptions-item label="最大特征数">
        {{ block.feature_params?.max_num_features || 4096 }}
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Block } from '@/types'

const props = defineProps<{
  block: Block
}>()

const matchingMethodText = computed(() => {
  switch (props.block.matching_method) {
    case 'sequential': return '序列匹配'
    case 'exhaustive': return '穷举匹配'
    case 'vocab_tree': return '词汇树匹配'
    default: return props.block.matching_method
  }
})

const gpuEnabled = computed(() => {
  return props.block.feature_params?.use_gpu ?? true
})
</script>

<style scoped>
.parameter-summary {
  font-size: 13px;
}
</style>
