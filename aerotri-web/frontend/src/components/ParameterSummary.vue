<template>
  <div class="parameter-summary">
    <el-descriptions :column="1" size="small" border>
      <el-descriptions-item label="算法">
        {{ algorithmText }}
      </el-descriptions-item>
      <el-descriptions-item label="匹配方法">
        {{ matchingMethodText }}
      </el-descriptions-item>
      <el-descriptions-item label="地理定位">
        {{ georefEnabled ? '启用' : '禁用' }}
      </el-descriptions-item>
      <el-descriptions-item v-if="georefEnabled" label="对齐最大误差(米)">
        {{ georefAlignmentMaxError }}
      </el-descriptions-item>
      <el-descriptions-item v-if="georefEnabled" label="最小公共影像数">
        {{ georefMinCommonImages }}
      </el-descriptions-item>
      <el-descriptions-item v-if="georefInfo" label="UTM EPSG">
        {{ georefInfo.epsg_utm }}
      </el-descriptions-item>
      <el-descriptions-item v-if="georefInfo?.origin_wgs84" label="Origin(WGS84)">
        lon={{ georefInfo.origin_wgs84.lon.toFixed(8) }},
        lat={{ georefInfo.origin_wgs84.lat.toFixed(8) }},
        h={{ georefInfo.origin_wgs84.h.toFixed(3) }}
      </el-descriptions-item>
      <el-descriptions-item v-if="georefInfo" label="geo_ref.json">
        <el-link :href="geoRefDownloadUrl" target="_blank" type="primary">下载</el-link>
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

const georefEnabled = computed(() => {
  return Boolean((props.block.mapper_params as any)?.georef_enabled)
})

const georefAlignmentMaxError = computed(() => {
  return (props.block.mapper_params as any)?.georef_alignment_max_error ?? 20
})

const georefMinCommonImages = computed(() => {
  return (props.block.mapper_params as any)?.georef_min_common_images ?? 3
})

type GeorefStats = {
  epsg_utm?: number
  origin_wgs84?: { lon: number; lat: number; h: number }
  origin_utm?: { E: number; N: number; H: number }
  geo_ref_path?: string
}

const georefInfo = computed<GeorefStats | null>(() => {
  const stats = (props.block.statistics || {}) as any
  return (stats.georef as GeorefStats) || null
})

const geoRefDownloadUrl = computed(() => {
  return `/api/blocks/${props.block.id}/georef/download`
})
</script>

<style scoped>
.parameter-summary {
  font-size: 13px;
}
</style>
