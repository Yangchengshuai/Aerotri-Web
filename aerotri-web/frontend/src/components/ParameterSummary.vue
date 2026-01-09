<template>
  <div class="parameter-summary">
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="算法">
        {{ algorithmText }}
      </el-descriptions-item>
      <el-descriptions-item label="匹配方法">
        {{ matchingMethodText }}
      </el-descriptions-item>
      <!-- OpenMVG-specific parameters -->
      <template v-if="block.algorithm === 'openmvg_global'">
        <el-descriptions-item label="特征密度">
          {{ block.openmvg_params?.feature_preset || 'NORMAL' }}
        </el-descriptions-item>
        <el-descriptions-item label="几何模型">
          {{ block.openmvg_params?.geometric_model === 'e' ? 'Essential Matrix' : 'Fundamental Matrix' }}
        </el-descriptions-item>
      </template>
      <!-- COLMAP/GLOMAP/InstantSfM parameters -->
      <template v-else>
        <el-descriptions-item label="GPU加速">
          {{ gpuEnabled ? '启用' : '禁用' }}
        </el-descriptions-item>
        <el-descriptions-item label="最大图像尺寸">
          {{ block.feature_params?.max_image_size || 2640 }}
        </el-descriptions-item>
        <el-descriptions-item label="最大特征数">
          {{ block.feature_params?.max_num_features || 20000 }}
        </el-descriptions-item>
      </template>
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
  // OpenMVG uses different matching method names
  if (props.block.algorithm === 'openmvg_global') {
    const pairMode = props.block.openmvg_params?.pair_mode || 'EXHAUSTIVE'
    const matchingMethod = props.block.openmvg_params?.matching_method || 'AUTO'
    if (pairMode === 'EXHAUSTIVE') {
      return `穷举配对 + ${matchingMethod}`
    } else {
      return `连续配对 + ${matchingMethod}`
    }
  }
  // COLMAP/GLOMAP/InstantSfM matching methods
  switch (props.block.matching_method) {
    case 'sequential': return '序列匹配'
    case 'exhaustive': return '穷举匹配'
    case 'vocab_tree': return '词汇树匹配'
    case 'spatial': return '空间匹配'
    default: return props.block.matching_method
  }
})

const algorithmText = computed(() => {
  switch (props.block.algorithm) {
    case 'glomap': return 'GLOMAP (全局式)'
    case 'colmap': return 'COLMAP (增量式)'
    case 'instantsfm': return 'InstantSfM (快速全局式)'
    case 'openmvg_global': return 'OpenMVG (全局式)'
    default: return props.block.algorithm
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
