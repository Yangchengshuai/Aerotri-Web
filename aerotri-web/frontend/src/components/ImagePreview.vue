<template>
  <div class="image-preview">
    <el-scrollbar height="200px">
      <div class="image-grid">
        <div
          v-for="image in images"
          :key="image.name"
          class="image-item"
          @click="selectedImage = image"
        >
          <el-image
            :src="getThumbnailUrl(image.name)"
            fit="cover"
            lazy
          >
            <template #error>
              <div class="image-error">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
        </div>
      </div>
    </el-scrollbar>

    <!-- Pagination -->
    <div class="pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        small
        @current-change="loadImages"
      />
    </div>

    <!-- Image Preview Dialog -->
    <el-dialog
      v-model="showPreview"
      :title="selectedImage?.name"
      width="80%"
      destroy-on-close
    >
      <div class="preview-content">
        <el-image
          v-if="selectedImage"
          :src="getImageUrl(selectedImage.name)"
          fit="contain"
          style="max-height: 70vh"
        />
      </div>
      <template #footer>
        <el-button type="danger" @click="handleDelete" :loading="deleting">
          删除图像
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import { imageApi } from '@/api'
import type { ImageInfo } from '@/types'

const props = defineProps<{
  blockId: string
}>()

const emit = defineEmits<{
  (e: 'update:total', total: number): void
}>()

const images = ref<ImageInfo[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)
const selectedImage = ref<ImageInfo | null>(null)
const deleting = ref(false)

const showPreview = computed({
  get: () => selectedImage.value !== null,
  set: (value) => {
    if (!value) selectedImage.value = null
  }
})

onMounted(() => {
  loadImages()
})

watch(() => props.blockId, () => {
  currentPage.value = 1
  loadImages()
})

async function loadImages() {
  loading.value = true
  try {
    const response = await imageApi.list(props.blockId, currentPage.value, pageSize)
    images.value = response.data.images
    total.value = response.data.total
    emit('update:total', total.value)
  } catch (e) {
    console.error('Failed to load images:', e)
  } finally {
    loading.value = false
  }
}

function getThumbnailUrl(imageName: string): string {
  return imageApi.getThumbnailUrl(props.blockId, imageName, 150)
}

function getImageUrl(imageName: string): string {
  return imageApi.getImageUrl(props.blockId, imageName)
}

async function handleDelete() {
  if (!selectedImage.value) return

  try {
    await ElMessageBox.confirm(
      `确定要删除图像 "${selectedImage.value.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )

    deleting.value = true
    await imageApi.delete(props.blockId, selectedImage.value.name)
    ElMessage.success('图像已删除')
    selectedImage.value = null
    await loadImages()
  } catch {
    // User cancelled
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.image-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  padding: 4px;
}

.image-item {
  aspect-ratio: 1;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}

.image-item:hover {
  transform: scale(1.05);
}

.image-item :deep(.el-image) {
  width: 100%;
  height: 100%;
}

.image-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
}

.pagination {
  display: flex;
  justify-content: center;
}

.preview-content {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
