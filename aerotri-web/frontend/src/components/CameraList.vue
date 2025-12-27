<template>
  <el-card class="panel-card" v-if="cameras.length > 0">
    <template #header>
      <div class="card-header">
        <span>相机列表</span>
        <el-text type="info" size="small">共 {{ cameras.length }} 个</el-text>
      </div>
    </template>
    
    <div class="camera-list-container">
      <!-- Search -->
      <el-input
        v-model="searchText"
        placeholder="搜索相机ID或图像名称"
        size="small"
        clearable
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <!-- List -->
      <el-scrollbar class="camera-list-scrollbar">
        <div class="camera-list">
          <div
            v-for="camera in filteredCameras"
            :key="camera.image_id"
            class="camera-item"
            :class="{ 'is-selected': camera.image_id === selectedCameraId }"
            @click="handleSelectCamera(camera.image_id)"
          >
            <div class="camera-item-content">
              <div class="camera-item-header">
                <el-text strong>ID: {{ camera.image_id }}</el-text>
                <el-tag size="small" type="info">{{ camera.num_points }} 点</el-tag>
              </div>
              <el-text type="info" size="small" class="camera-item-name">
                {{ camera.image_name }}
              </el-text>
              <div v-if="camera.x !== null && camera.y !== null && camera.z !== null" class="camera-item-position">
                <el-text size="small" type="info">
                  位置: ({{ camera.x.toFixed(1) }}, {{ camera.y.toFixed(1) }}, {{ camera.z.toFixed(1) }})
                </el-text>
              </div>
            </div>
          </div>
        </div>
      </el-scrollbar>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useCameraSelectionStore } from '@/stores/cameraSelection'
import type { CameraInfo } from '@/types'

const cameraSelectionStore = useCameraSelectionStore()

const cameras = computed(() => cameraSelectionStore.cameras)
const selectedCameraId = computed(() => cameraSelectionStore.selectedCameraId)

const searchText = ref('')

const filteredCameras = computed(() => {
  if (!searchText.value.trim()) {
    return cameras.value
  }
  
  const query = searchText.value.toLowerCase().trim()
  return cameras.value.filter(camera => {
    return (
      camera.image_id.toString().includes(query) ||
      camera.image_name.toLowerCase().includes(query)
    )
  })
})

function handleSelectCamera(cameraId: number) {
  cameraSelectionStore.setSelectedCamera(cameraId)
}
</script>

<style scoped>
.panel-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-list-container {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.search-input {
  margin-bottom: 12px;
}

.camera-list-scrollbar {
  flex: 1;
  min-height: 0;
}

.camera-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.camera-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
}

.camera-item:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.camera-item.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.camera-item-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.camera-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-item-name {
  word-break: break-all;
  line-height: 1.4;
}

.camera-item-position {
  margin-top: 4px;
}
</style>

