<template>
  <div 
    v-if="isOpen" 
    class="camera-detail-panel"
    :style="{ height: panelHeight + 'px' }"
  >
    <!-- Drag handle -->
    <div class="drag-handle" @mousedown="startDrag">
      <el-icon><Rank /></el-icon>
    </div>

    <!-- Panel content -->
    <div class="panel-content">
      <!-- Header -->
      <div class="panel-header">
        <div class="header-left">
          <h3>相机详情</h3>
          <el-text v-if="camera" type="info" size="small">
            {{ camera.image_name }}
          </el-text>
        </div>
        <div class="header-right">
          <el-button 
            text 
            size="small" 
            @click="handleViewOriginal"
            :disabled="!camera"
          >
            <el-icon><View /></el-icon>
            查看原图
          </el-button>
          <el-button 
            text 
            size="small" 
            type="danger"
            @click="handleDelete"
            :disabled="!camera || deleting"
            :loading="deleting"
          >
            <el-icon><Delete /></el-icon>
            删除图像
          </el-button>
          <el-button 
            text 
            size="small" 
            @click="closePanel"
          >
            <el-icon><Close /></el-icon>
            关闭
          </el-button>
        </div>
      </div>

      <!-- Content -->
      <div class="panel-body" v-if="camera">
        <el-row :gutter="16">
          <!-- Image preview -->
          <el-col :span="16">
            <div class="image-section">
              <div class="image-container" v-loading="imageLoading">
                <img
                  v-if="imageUrl && !imageError"
                  :src="imageUrl"
                  :alt="camera.image_name"
                  @load="imageLoading = false"
                  @error="handleImageError"
                  class="camera-image"
                  :style="{ transform: `scale(${imageScale})` }"
                />
                <div v-else-if="imageError" class="image-error">
                  <el-icon :size="48"><Picture /></el-icon>
                  <p>图像加载失败</p>
                </div>
              </div>
              <div class="image-controls">
                <el-button-group>
                  <el-button size="small" @click="zoomOut" :disabled="imageScale <= 0.1">
                    <el-icon><ZoomOut /></el-icon>
                  </el-button>
                  <el-button size="small" @click="resetZoom">
                    {{ Math.round(imageScale * 100) }}%
                  </el-button>
                  <el-button size="small" @click="zoomIn" :disabled="imageScale >= 3">
                    <el-icon><ZoomIn /></el-icon>
                  </el-button>
                </el-button-group>
                <el-button-group style="margin-left: 8px">
                  <el-button 
                    size="small" 
                    :type="fitMode === 'contain' ? 'primary' : 'default'"
                    @click="fitMode = 'contain'"
                  >
                    适应容器
                  </el-button>
                  <el-button 
                    size="small" 
                    :type="fitMode === 'original' ? 'primary' : 'default'"
                    @click="fitMode = 'original'"
                  >
                    原始尺寸
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </el-col>

          <!-- Camera info -->
          <el-col :span="8">
            <div class="info-section">
              <h4>相机信息</h4>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="相机ID">
                  {{ camera.image_id }}
                </el-descriptions-item>
                <el-descriptions-item label="图像名称">
                  <el-text copyable>{{ camera.image_name }}</el-text>
                </el-descriptions-item>
                <el-descriptions-item label="相机模型ID">
                  {{ camera.camera_id }}
                </el-descriptions-item>
                <el-descriptions-item label="3D点数量">
                  {{ camera.num_points }}
                </el-descriptions-item>
                <el-descriptions-item label="位置" v-if="camera.x !== null && camera.y !== null && camera.z !== null">
                  X: {{ camera.x.toFixed(2) }}<br>
                  Y: {{ camera.y.toFixed(2) }}<br>
                  Z: {{ camera.z.toFixed(2) }}
                </el-descriptions-item>
                <el-descriptions-item label="姿态（四元数）">
                  qw: {{ camera.qw.toFixed(4) }}<br>
                  qx: {{ camera.qx.toFixed(4) }}<br>
                  qy: {{ camera.qy.toFixed(4) }}<br>
                  qz: {{ camera.qz.toFixed(4) }}
                </el-descriptions-item>
                <el-descriptions-item label="平移">
                  tx: {{ camera.tx.toFixed(4) }}<br>
                  ty: {{ camera.ty.toFixed(4) }}<br>
                  tz: {{ camera.tz.toFixed(4) }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Rank, View, Delete, Close, ZoomIn, ZoomOut, Picture } from '@element-plus/icons-vue'
import { useCameraSelectionStore } from '@/stores/cameraSelection'
import { imageApi } from '@/api'
import type { CameraInfo } from '@/types'

const cameraSelectionStore = useCameraSelectionStore()

const isOpen = computed(() => cameraSelectionStore.isPanelOpen && cameraSelectionStore.selectedCamera !== null)
const camera = computed(() => cameraSelectionStore.selectedCamera)
const blockId = computed(() => cameraSelectionStore.blockId)

const imageUrl = ref<string | null>(null)
const imageLoading = ref(false)
const imageError = ref(false)
const imageScale = ref(1.0)
const fitMode = ref<'contain' | 'original'>('contain')
const deleting = ref(false)

const panelHeight = ref(400)
const minHeight = 200
const maxHeight = 800
let isDragging = false
let dragStartY = 0
let dragStartHeight = 0

// Load image when camera changes
watch(() => camera.value?.image_name, (imageName) => {
  if (imageName && blockId.value) {
    loadImage(imageName)
  } else {
    imageUrl.value = null
    imageError.value = false
  }
  imageScale.value = 1.0
  fitMode.value = 'contain'
}, { immediate: true })

// Watch panel open state
watch(isOpen, (open) => {
  if (open && camera.value) {
    loadImage(camera.value.image_name)
  }
})

function loadImage(imageName: string) {
  if (!blockId.value) return
  
  imageLoading.value = true
  imageError.value = false
  imageUrl.value = imageApi.getImageUrl(blockId.value, imageName)
}

function handleImageError() {
  imageLoading.value = false
  imageError.value = true
  ElMessage.error('图像加载失败')
}

function zoomIn() {
  imageScale.value = Math.min(imageScale.value + 0.1, 3)
}

function zoomOut() {
  imageScale.value = Math.max(imageScale.value - 0.1, 0.1)
}

function resetZoom() {
  imageScale.value = 1.0
}

function closePanel() {
  cameraSelectionStore.closePanel()
}

function handleViewOriginal() {
  if (!camera.value || !blockId.value) return
  const url = imageApi.getImageUrl(blockId.value, camera.value.image_name)
  window.open(url, '_blank')
}

async function handleDelete() {
  if (!camera.value || !blockId.value) return

  try {
    await ElMessageBox.confirm(
      `确定要删除图像 "${camera.value.image_name}" 吗？\n\n删除后需要重新运行空三才能生效。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    deleting.value = true
    await imageApi.delete(blockId.value, camera.value.image_name)
    
    ElMessage.success('图像删除成功')
    
    // Remove camera from store (this will also clear selection)
    cameraSelectionStore.removeCamera(camera.value.image_id)
    
    // Emit event to parent to update 3D scene
    // The store change will trigger ThreeViewer to update
    
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
      ElMessage.error('删除失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  } finally {
    deleting.value = false
  }
}

function startDrag(event: MouseEvent) {
  isDragging = true
  dragStartY = event.clientY
  dragStartHeight = panelHeight.value
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  event.preventDefault()
}

function onDrag(event: MouseEvent) {
  if (!isDragging) return
  const deltaY = dragStartY - event.clientY
  const newHeight = Math.max(minHeight, Math.min(maxHeight, dragStartHeight + deltaY))
  panelHeight.value = newHeight
}

function stopDrag() {
  isDragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  // Save preference
  localStorage.setItem('cameraPanelHeight', panelHeight.value.toString())
}

onMounted(() => {
  // Load saved height preference
  const saved = localStorage.getItem('cameraPanelHeight')
  if (saved) {
    const height = parseInt(saved, 10)
    if (height >= minHeight && height <= maxHeight) {
      panelHeight.value = height
    }
  }
})

onUnmounted(() => {
  stopDrag()
})
</script>

<style scoped>
.camera-detail-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 1px solid #e4e7ed;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  display: flex;
  flex-direction: column;
  transition: height 0.3s ease;
}

.drag-handle {
  height: 8px;
  background: #f5f7fa;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #e4e7ed;
  user-select: none;
}

.drag-handle:hover {
  background: #e4e7ed;
}

.drag-handle .el-icon {
  color: #909399;
  font-size: 12px;
}

.panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
}

.header-left h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 8px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.image-section {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: auto;
  min-height: 200px;
}

.camera-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.2s;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  padding: 24px;
}

.image-error p {
  margin: 8px 0 0 0;
  font-size: 14px;
}

.image-controls {
  margin-top: 12px;
  display: flex;
  align-items: center;
}

.info-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
}

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>

