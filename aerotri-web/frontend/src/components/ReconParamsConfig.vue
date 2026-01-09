<template>
  <div class="recon-params-config">
    <el-collapse v-model="activeStages">
      <el-collapse-item 
        v-for="stage in stages" 
        :key="stage.key" 
        :name="stage.key"
      >
        <template #title>
          <div class="stage-header">
            <span class="stage-title">{{ stage.label }}</span>
          </div>
        </template>
        
        <div class="stage-params">
          <el-form 
            :model="localParams[stage.key]" 
            label-width="120px" 
            size="small"
          >
            <el-form-item 
              v-for="(meta, paramKey) in schema?.[stage.key]" 
              :key="paramKey"
              :label="meta.label"
            >
              <template v-if="meta.type === 'int'">
                <el-input-number
                  v-model="localParams[stage.key][paramKey]"
                  :min="meta.min"
                  :max="meta.max"
                  :step="1"
                  controls-position="right"
                  style="width: 140px"
                  @change="onParamChange"
                />
              </template>
              <template v-else-if="meta.type === 'float'">
                <el-input-number
                  v-model="localParams[stage.key][paramKey]"
                  :min="meta.min"
                  :max="meta.max"
                  :step="meta.step || 0.1"
                  :precision="2"
                  controls-position="right"
                  style="width: 140px"
                  @change="onParamChange"
                />
              </template>
              <span class="param-desc">{{ meta.description }}</span>
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { 
  ReconstructionParams, 
  ReconQualityPreset, 
  ReconPresets, 
  ReconParamsSchema,
  DensifyParams,
  MeshParams,
  RefineParams,
  TextureParams,
} from '@/types'
import { reconstructionApi } from '@/api'

interface LocalParams {
  densify: DensifyParams
  mesh: MeshParams
  refine: RefineParams
  texture: TextureParams
}

const props = defineProps<{
  preset: ReconQualityPreset
  modelValue: ReconstructionParams | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: ReconstructionParams): void
  (e: 'custom-changed'): void
}>()

const presets = ref<ReconPresets | null>(null)
const schema = ref<ReconParamsSchema | null>(null)
const stageLabels = ref<Record<string, string>>({})
const loading = ref(true)
const activeStages = ref<string[]>(['densify', 'mesh', 'refine', 'texture'])

const localParams = ref<LocalParams>({
  densify: {},
  mesh: {},
  refine: {},
  texture: {},
})

const stages = computed(() => [
  { key: 'densify' as const, label: stageLabels.value.densify || '稠密点云 (DensifyPointCloud)' },
  { key: 'mesh' as const, label: stageLabels.value.mesh || '网格重建 (ReconstructMesh)' },
  { key: 'refine' as const, label: stageLabels.value.refine || '网格优化 (RefineMesh)' },
  { key: 'texture' as const, label: stageLabels.value.texture || '纹理贴图 (TextureMesh)' },
])

// Load presets and schema from API
async function loadConfig() {
  loading.value = true
  try {
    const [presetsRes, schemaRes] = await Promise.all([
      reconstructionApi.getPresets(),
      reconstructionApi.getParamsSchema(),
    ])
    presets.value = presetsRes.data.presets
    stageLabels.value = presetsRes.data.stage_labels
    schema.value = schemaRes.data.schema
    
    // Initialize with preset values
    applyPreset(props.preset)
  } catch (e) {
    console.error('Failed to load reconstruction config:', e)
  } finally {
    loading.value = false
  }
}

// Apply a preset to local params
function applyPreset(preset: ReconQualityPreset) {
  if (!presets.value) return
  
  const presetParams = presets.value[preset]
  if (!presetParams) return
  
  localParams.value = {
    densify: { ...presetParams.densify },
    mesh: { ...presetParams.mesh },
    refine: { ...presetParams.refine },
    texture: { ...presetParams.texture },
  }
  
  emitParams()
}

// Handle parameter change
function onParamChange() {
  emitParams()
  emit('custom-changed')
}

// Emit current params
function emitParams() {
  const params: ReconstructionParams = {
    densify: { ...localParams.value.densify },
    mesh: { ...localParams.value.mesh },
    refine: { ...localParams.value.refine },
    texture: { ...localParams.value.texture },
  }
  emit('update:modelValue', params)
}

// Watch preset changes
watch(() => props.preset, (newPreset) => {
  applyPreset(newPreset)
})

// Initialize on mount
onMounted(() => {
  loadConfig()
})

// Expose method to reset to preset
defineExpose({
  applyPreset,
})
</script>

<style scoped>
.recon-params-config {
  margin-top: 12px;
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-title {
  font-weight: 500;
}

.stage-params {
  padding: 8px 0;
}

.param-desc {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

:deep(.el-collapse-item__header) {
  font-size: 14px;
  background: #f5f7fa;
  padding: 0 12px;
  border-radius: 4px;
}

:deep(.el-collapse-item__content) {
  padding: 12px;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}

:deep(.el-form-item__label) {
  font-size: 13px;
}
</style>
