<template>
  <div class="parameter-form">
    <el-form :model="formData" label-width="160px" label-position="right">
      <!-- Algorithm Selection -->
      <el-divider content-position="left">基本设置</el-divider>
      
      <el-form-item label="重建算法">
        <el-radio-group v-model="formData.algorithm">
          <el-radio value="glomap">GLOMAP (全局式)</el-radio>
          <el-radio value="colmap">COLMAP (增量式)</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="匹配方法">
        <el-select v-model="formData.matching_method" style="width: 100%">
          <el-option label="序列匹配 (Sequential)" value="sequential" />
          <el-option label="穷举匹配 (Exhaustive)" value="exhaustive" />
          <el-option label="词汇树匹配 (Vocab Tree)" value="vocab_tree" />
        </el-select>
      </el-form-item>

      <!-- Feature Extraction -->
      <el-divider content-position="left">特征提取</el-divider>

      <el-form-item label="GPU 加速">
        <el-switch v-model="formData.feature_params.use_gpu" />
      </el-form-item>

      <el-form-item label="相机模型">
        <el-select v-model="formData.feature_params.camera_model" style="width: 100%">
          <el-option label="SIMPLE_RADIAL" value="SIMPLE_RADIAL" />
          <el-option label="PINHOLE" value="PINHOLE" />
          <el-option label="SIMPLE_PINHOLE" value="SIMPLE_PINHOLE" />
          <el-option label="RADIAL" value="RADIAL" />
          <el-option label="OPENCV" value="OPENCV" />
        </el-select>
      </el-form-item>

      <el-form-item label="单相机模式">
        <el-switch v-model="formData.feature_params.single_camera" />
        <el-text type="info" size="small" style="margin-left: 8px">
          所有图像使用相同相机参数
        </el-text>
      </el-form-item>

      <el-form-item label="最大图像尺寸">
        <el-input-number
          v-model="formData.feature_params.max_image_size"
          :min="500"
          :max="8000"
          :step="100"
        />
        <el-text type="info" size="small" style="margin-left: 8px">
          像素
        </el-text>
      </el-form-item>

      <el-form-item label="最大特征数">
        <el-input-number
          v-model="formData.feature_params.max_num_features"
          :min="1000"
          :max="16384"
          :step="1000"
        />
      </el-form-item>

      <!-- Matching Parameters -->
      <el-divider content-position="left">特征匹配</el-divider>

      <el-form-item label="匹配 GPU 加速">
        <el-switch v-model="formData.matching_params.use_gpu" />
      </el-form-item>

      <el-form-item label="序列重叠" v-if="formData.matching_method === 'sequential'">
        <el-input-number
          v-model="formData.matching_params.overlap"
          :min="5"
          :max="100"
          :step="5"
        />
        <el-text type="info" size="small" style="margin-left: 8px">
          窗口大小
        </el-text>
      </el-form-item>

      <!-- Mapper Parameters -->
      <el-divider content-position="left">Mapper 参数</el-divider>

      <template v-if="formData.algorithm === 'colmap'">
        <el-form-item label="BA GPU 加速">
          <el-switch v-model="formData.mapper_params.ba_use_gpu" />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="GlobalPositioning GPU">
          <el-switch v-model="formData.mapper_params.global_positioning_use_gpu" />
        </el-form-item>

        <el-form-item label="GPU Solver 最小图像数">
          <el-input-number
            v-model="formData.mapper_params.global_positioning_min_num_images_gpu_solver"
            :min="1"
            :max="100"
          />
        </el-form-item>

        <el-form-item label="BundleAdjustment GPU">
          <el-switch v-model="formData.mapper_params.bundle_adjustment_use_gpu" />
        </el-form-item>
      </template>
    </el-form>

    <div class="form-actions">
      <el-button @click="$emit('cancel')">取消</el-button>
      <el-button type="primary" @click="handleSave">保存</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { Block, FeatureParams, MatchingParams, GlomapMapperParams, ColmapMapperParams } from '@/types'

const props = defineProps<{
  block: Block
}>()

const emit = defineEmits<{
  (e: 'save', params: Partial<Block>): void
  (e: 'cancel'): void
}>()

// Default parameters
const defaultFeatureParams: FeatureParams = {
  use_gpu: true,
  gpu_index: 0,
  max_image_size: 2000,
  max_num_features: 4096,
  camera_model: 'SIMPLE_RADIAL',
  single_camera: true,
}

const defaultMatchingParams: MatchingParams = {
  method: 'sequential',
  overlap: 20,
  use_gpu: true,
  gpu_index: 0,
}

const defaultGlomapParams: GlomapMapperParams = {
  global_positioning_use_gpu: true,
  global_positioning_gpu_index: 0,
  global_positioning_min_num_images_gpu_solver: 1,
  bundle_adjustment_use_gpu: true,
  bundle_adjustment_gpu_index: 0,
  bundle_adjustment_min_num_images_gpu_solver: 1,
}

const defaultColmapParams: ColmapMapperParams = {
  ba_use_gpu: true,
  ba_gpu_index: 0,
}

const formData = reactive({
  algorithm: props.block.algorithm,
  matching_method: props.block.matching_method,
  feature_params: { ...defaultFeatureParams, ...props.block.feature_params },
  matching_params: { ...defaultMatchingParams, ...props.block.matching_params },
  mapper_params: props.block.algorithm === 'glomap'
    ? { ...defaultGlomapParams, ...(props.block.mapper_params as GlomapMapperParams) }
    : { ...defaultColmapParams, ...(props.block.mapper_params as ColmapMapperParams) },
})

// Watch algorithm changes to update mapper params
watch(() => formData.algorithm, (algorithm) => {
  if (algorithm === 'glomap') {
    formData.mapper_params = { ...defaultGlomapParams }
  } else {
    formData.mapper_params = { ...defaultColmapParams }
  }
})

// Keep matching_params.method consistent with matching_method selection
watch(() => formData.matching_method, (method) => {
  formData.matching_params.method = method
}, { immediate: true })

function handleSave() {
  emit('save', {
    algorithm: formData.algorithm,
    matching_method: formData.matching_method,
    feature_params: formData.feature_params,
    matching_params: formData.matching_params,
    mapper_params: formData.mapper_params,
  })
}
</script>

<style scoped>
.parameter-form {
  padding: 0 20px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}
</style>
