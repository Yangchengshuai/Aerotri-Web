<template>
  <div class="parameter-form">
    <el-form :model="formData" label-width="160px" label-position="right">
      <!-- Algorithm Selection -->
      <el-divider content-position="left">基本设置</el-divider>
      
      <el-form-item label="重建算法">
        <el-radio-group v-model="formData.algorithm">
          <el-radio value="glomap">GLOMAP (全局式)</el-radio>
          <el-radio value="colmap">COLMAP (增量式)</el-radio>
          <el-radio value="instantsfm">InstantSfM (快速全局式)</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="匹配方法">
        <el-select v-model="formData.matching_method" style="width: 100%">
          <el-option label="序列匹配 (Sequential)" value="sequential" />
          <el-option label="穷举匹配 (Exhaustive)" value="exhaustive" />
          <el-option label="词汇树匹配 (Vocab Tree)" value="vocab_tree" />
          <el-option label="空间匹配 (Spatial)" value="spatial" />
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

      <!-- Vocab Tree parameters -->
      <el-form-item
        label="词汇树路径"
        v-if="formData.matching_method === 'vocab_tree'"
      >
        <el-input
          v-model="formData.matching_params.vocab_tree_path"
          placeholder="例如：/path/to/vocab_tree.bin，留空则使用服务器默认配置（如有）"
          clearable
        />
      </el-form-item>

      <!-- Spatial matching parameters -->
      <template v-if="formData.matching_method === 'spatial'">
        <el-form-item label="最大邻居数">
          <el-input-number
            v-model="formData.matching_params.spatial_max_num_neighbors"
            :min="1"
            :max="200"
            :step="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            每张影像匹配的空间最近邻影像数量
          </el-text>
        </el-form-item>

        <el-form-item label="坐标类型为 GPS">
          <el-switch v-model="formData.matching_params.spatial_is_gps" />
          <el-text type="info" size="small" style="margin-left: 8px">
            勾选表示使用经纬度/GPS 坐标进行空间最近邻搜索
          </el-text>
        </el-form-item>

        <el-form-item label="忽略高度 (Z)">
          <el-switch v-model="formData.matching_params.spatial_ignore_z" />
          <el-text type="info" size="small" style="margin-left: 8px">
            对只有平面精度的航测数据，可忽略高度分量，只按平面距离匹配
          </el-text>
        </el-form-item>
      </template>

      <!-- Mapper Parameters -->
      <el-divider content-position="left">Mapper 参数</el-divider>

      <template v-if="formData.algorithm === 'colmap'">
        <el-form-item label="使用 Pose Prior">
          <el-switch v-model="(formData.mapper_params as any).use_pose_prior" />
          <el-text type="info" size="small" style="margin-left: 8px">
            使用图像 EXIF GPS（lat/lon/alt）位置先验加速重建
          </el-text>
        </el-form-item>

        <el-form-item label="BA GPU 加速">
          <el-switch v-model="formData.mapper_params.ba_use_gpu" />
        </el-form-item>
      </template>

      <template v-else-if="formData.algorithm === 'glomap'">
        <el-form-item label="使用 Pose Prior">
          <el-switch v-model="(formData.mapper_params as any).use_pose_prior" />
          <el-text type="info" size="small" style="margin-left: 8px">
            使用图像 EXIF GPS（lat/lon/alt）位置先验加速 GP/BA
          </el-text>
        </el-form-item>

        <el-form-item label="GlobalPositioning GPU">
          <el-switch v-model="formData.mapper_params.global_positioning_use_gpu" />
        </el-form-item>

        <el-form-item label="BundleAdjustment GPU">
          <el-switch v-model="formData.mapper_params.bundle_adjustment_use_gpu" />
        </el-form-item>
      </template>

      <template v-else-if="formData.algorithm === 'instantsfm'">
        <el-form-item label="导出文本格式">
          <el-switch v-model="formData.mapper_params.export_txt" />
          <el-text type="info" size="small" style="margin-left: 8px">
            导出 cameras.txt, images.txt, points3D.txt
          </el-text>
        </el-form-item>

        <el-form-item label="禁用深度信息">
          <el-switch v-model="formData.mapper_params.disable_depths" />
        </el-form-item>

        <el-form-item label="自定义配置文件名">
          <el-input
            v-model="formData.mapper_params.manual_config_name"
            placeholder="留空使用默认配置 (colmap)"
            clearable
          />
        </el-form-item>

        <el-form-item label="GPU 索引">
          <el-input-number
            v-model="formData.mapper_params.gpu_index"
            :min="0"
            :max="15"
            :step="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            指定使用的 GPU 设备编号（0-15）
          </el-text>
        </el-form-item>

        <el-form-item label="束调整迭代次数">
          <el-input-number
            v-model="formData.mapper_params.num_iteration_bundle_adjustment"
            :min="1"
            :max="10"
          />
        </el-form-item>

        <el-form-item label="束调整最大迭代次数">
          <el-input-number
            v-model="formData.mapper_params.bundle_adjustment_max_iterations"
            :min="50"
            :max="500"
            :step="50"
          />
        </el-form-item>

        <el-form-item label="束调整函数容差">
          <el-input-number
            v-model="formData.mapper_params.bundle_adjustment_function_tolerance"
            :min="1e-6"
            :max="1e-2"
            :step="1e-4"
            :precision="6"
          />
        </el-form-item>

        <el-form-item label="全局定位最大迭代次数">
          <el-input-number
            v-model="formData.mapper_params.global_positioning_max_iterations"
            :min="50"
            :max="200"
            :step="10"
          />
        </el-form-item>

        <el-form-item label="全局定位函数容差">
          <el-input-number
            v-model="formData.mapper_params.global_positioning_function_tolerance"
            :min="1e-6"
            :max="1e-2"
            :step="1e-4"
            :precision="6"
          />
        </el-form-item>

        <el-form-item label="最小匹配数">
          <el-input-number
            v-model="formData.mapper_params.min_num_matches"
            :min="10"
            :max="100"
            :step="5"
          />
        </el-form-item>

        <el-form-item label="最小三角化角度">
          <el-input-number
            v-model="formData.mapper_params.min_triangulation_angle"
            :min="0.5"
            :max="5.0"
            :step="0.5"
            :precision="1"
          />
          <el-text type="info" size="small" style="margin-left: 8px">
            度
          </el-text>
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
import type { Block, FeatureParams, MatchingParams, GlomapMapperParams, ColmapMapperParams, InstantsfmMapperParams } from '@/types'

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
  max_image_size: 2640,
  max_num_features: 12000,
  camera_model: 'SIMPLE_RADIAL',
  single_camera: true,
}

const defaultMatchingParams: MatchingParams = {
  method: 'sequential',
  overlap: 10,
  use_gpu: true,
  gpu_index: 0,
  vocab_tree_path: undefined,
  spatial_max_num_neighbors: 50,
  spatial_is_gps: true,
  spatial_ignore_z: false,
}

const defaultGlomapParams: GlomapMapperParams = {
  use_pose_prior: false,
  global_positioning_use_gpu: true,
  global_positioning_gpu_index: 0,
  bundle_adjustment_use_gpu: true,
  bundle_adjustment_gpu_index: 0,
}

const defaultColmapParams: ColmapMapperParams = {
  use_pose_prior: false,
  ba_use_gpu: true,
  ba_gpu_index: 0,
}

const defaultInstantsfmParams: InstantsfmMapperParams = {
  export_txt: true,
  disable_depths: false,
  manual_config_name: null,
  gpu_index: 0,
  num_iteration_bundle_adjustment: 3,
  bundle_adjustment_max_iterations: 200,
  bundle_adjustment_function_tolerance: 5e-4,
  global_positioning_max_iterations: 100,
  global_positioning_function_tolerance: 5e-4,
  min_num_matches: 30,
  min_triangulation_angle: 1.5,
}

const formData = reactive({
  algorithm: props.block.algorithm,
  matching_method: props.block.matching_method,
  feature_params: { ...defaultFeatureParams, ...props.block.feature_params },
  matching_params: { ...defaultMatchingParams, ...props.block.matching_params },
  mapper_params: props.block.algorithm === 'glomap'
    ? { ...defaultGlomapParams, ...(props.block.mapper_params as GlomapMapperParams) }
    : props.block.algorithm === 'instantsfm'
    ? { ...defaultInstantsfmParams, ...(props.block.mapper_params as InstantsfmMapperParams) }
    : { ...defaultColmapParams, ...(props.block.mapper_params as ColmapMapperParams) },
})

// Watch algorithm changes to update mapper params
watch(() => formData.algorithm, (algorithm) => {
  if (algorithm === 'glomap') {
    formData.mapper_params = { ...defaultGlomapParams }
  } else if (algorithm === 'instantsfm') {
    formData.mapper_params = { ...defaultInstantsfmParams }
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
