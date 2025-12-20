<template>
  <el-card class="panel-card partition-panel">
    <template #header>
      <div class="card-header">
        <span>分区模式（大数据集）</span>
        <div class="header-actions">
          <el-switch
            v-model="form.partition_enabled"
            :disabled="loading || blockStatus === 'running'"
            active-text="启用"
            inactive-text="关闭"
            @change="handleToggle"
          />
        </div>
      </div>
    </template>

    <div class="partition-content">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="hint-alert"
      >
        为数千张以上的大数据集推荐开启分区模式：
        按文件名顺序切块，前后分区重叠 {{ form.partition_params.overlap }} 张，先全局特征+匹配，再分区建图+合并。
      </el-alert>

      <el-form
        label-width="110px"
        size="small"
        :disabled="!form.partition_enabled || loading || blockStatus === 'running'"
      >
        <el-form-item label="每分区图像数">
          <el-input-number
            v-model="form.partition_params.partition_size"
            :min="10"
            :step="50"
          />
        </el-form-item>

        <el-form-item label="分区重叠数">
          <el-input-number
            v-model="form.partition_params.overlap"
            :min="0"
            :max="form.partition_params.partition_size - 1"
            :step="10"
          />
        </el-form-item>

        <el-form-item label="流水线模式">
          <el-select v-model="form.sfm_pipeline_mode" disabled>
            <el-option
              label="全局特征+匹配 + 分区 mapper（当前使用）"
              value="global_feat_match"
            />
            <el-option
              label="分区独立 SfM + 合并（即将支持）"
              value="per_partition_full"
              disabled
            />
          </el-select>
        </el-form-item>

        <el-form-item label="合并策略">
          <el-select v-model="form.merge_strategy">
            <el-option
              label="Sim3 合并（支持尺度对齐，适用于不同相机内参）"
              value="sim3_keep_one"
            />
            <el-option
              label="刚性合并（重叠相机保留后一个分区的位姿）"
              value="rigid_keep_one"
              disabled
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="small"
            :loading="saving"
            :disabled="blockStatus === 'running'"
            @click="handleSave"
          >
            保存配置
          </el-button>
          <el-button
            size="small"
            :loading="previewLoading"
            :disabled="!form.partition_enabled || blockStatus === 'running'"
            @click="handlePreview"
          >
            预览分区
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider content-position="left">分区预览</el-divider>

      <div v-if="preview.total_images === 0" class="preview-empty">
        <el-text type="info" size="small">
          暂无分区预览，可点击「预览分区」查看当前参数下的分区结果。
        </el-text>
      </div>
      <div v-else>
        <el-text type="info" size="small" class="preview-summary">
          共 {{ preview.total_images }} 张图像，预览 {{ preview.partitions.length }} 个分区
        </el-text>
        <el-table
          :data="preview.partitions"
          size="small"
          border
          style="width: 100%; margin-top: 8px"
        >
          <el-table-column prop="index" label="#" width="50">
            <template #default="scope">
              {{ scope.row.index + 1 }}
            </template>
          </el-table-column>
          <el-table-column prop="name" label="分区" width="70" />
          <el-table-column prop="image_count" label="图像数" width="80" />
          <el-table-column prop="overlap_with_prev" label="与前重叠" width="90" />
          <el-table-column prop="overlap_with_next" label="与后重叠" width="90" />
          <el-table-column prop="image_start_name" label="起始文件名" min-width="140" />
          <el-table-column prop="image_end_name" label="结束文件名" min-width="140" />
        </el-table>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { partitionApi } from '@/api'

const props = defineProps<{
  blockId: string
  blockStatus?: string | null
}>()

const loading = ref(false)
const saving = ref(false)
const previewLoading = ref(false)

const form = reactive({
  partition_enabled: false,
  partition_strategy: 'name_range_with_overlap',
  partition_params: {
    partition_size: 1000,
    overlap: 150,
  } as { partition_size: number; overlap: number },
  sfm_pipeline_mode: 'global_feat_match',
  merge_strategy: 'sim3_keep_one',
})

const preview = reactive<{
  total_images: number
  partitions: Array<{
    index: number
    name: string
    image_start_name: string | null
    image_end_name: string | null
    image_count: number
    overlap_with_prev: number
    overlap_with_next: number
  }>
}>({
  total_images: 0,
  partitions: [],
})

const blockStatus = computed(() => props.blockStatus ?? null)

async function loadConfig() {
  loading.value = true
  try {
    const res = await partitionApi.getConfig(props.blockId)
    const data = res.data
    form.partition_enabled = data.partition_enabled
    form.partition_strategy = data.partition_strategy || 'name_range_with_overlap'
    form.partition_params = {
      partition_size:
        (data.partition_params?.partition_size as number | undefined) ?? 1000,
      overlap:
        (data.partition_params?.overlap as number | undefined) ?? 150,
    }
    form.sfm_pipeline_mode = data.sfm_pipeline_mode || 'global_feat_match'
    form.merge_strategy = data.merge_strategy || 'sim3_keep_one'

    // 预加载一次列表（不强求）
    preview.total_images = 0
    preview.partitions = []
  } catch (e) {
    // 首次没有配置时接口也会返回默认结构，这里仅做兜底
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await partitionApi.updateConfig(props.blockId, {
      partition_enabled: form.partition_enabled,
      partition_strategy: form.partition_strategy,
      partition_params: {
        partition_size: form.partition_params.partition_size,
        overlap: form.partition_params.overlap,
      },
      sfm_pipeline_mode: form.sfm_pipeline_mode,
      merge_strategy: form.merge_strategy,
    })
    ElMessage.success('分区配置已保存')
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '保存分区配置失败')
  } finally {
    saving.value = false
  }
}

async function handlePreview() {
  previewLoading.value = true
  try {
    const res = await partitionApi.preview(
      props.blockId,
      form.partition_params.partition_size,
      form.partition_params.overlap,
    )
    const data = res.data
    preview.total_images = data.total_images
    preview.partitions = data.partitions.map(p => ({
      index: p.index,
      name: p.name,
      image_start_name: p.image_start_name,
      image_end_name: p.image_end_name,
      image_count: p.image_count,
      overlap_with_prev: p.overlap_with_prev,
      overlap_with_next: p.overlap_with_next,
    }))
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || '预览分区失败')
  } finally {
    previewLoading.value = false
  }
}

function handleToggle() {
  // 仅切换开关不自动保存，防止误触；交给“保存配置”按钮
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.partition-panel {
  margin-top: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.partition-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hint-alert {
  margin-bottom: 8px;
}

.preview-empty {
  padding: 4px 0;
}

.preview-summary {
  margin-bottom: 4px;
}
</style>


