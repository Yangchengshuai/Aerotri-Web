<template>
  <el-card class="panel-card" v-if="cameras.length > 0">
    <template #header>
      <div class="card-header">
        <span>相机列表</span>
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-text type="info" size="small">共 {{ cameras.length }} 个</el-text>
          <el-tooltip :content="`重投影误差 > ${errorThreshold.toFixed(1)} px 视为问题相机（蓝色标识），≤ 阈值为正常相机（绿色标识）`" placement="top">
            <el-icon style="cursor: help;"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
      </div>
    </template>
    
    <div class="camera-list-container">
      <!-- Controls -->
      <div class="controls-row">
        <el-checkbox 
          v-model="showOnlyProblemCamerasInList" 
          size="small"
          @change="handleFilterChange"
        >
          只看问题相机
        </el-checkbox>
        <el-select
          v-model="sortOrder"
          size="small"
          style="width: 150px"
          @change="handleSortChange"
        >
          <el-option label="按图像 ID 升序" value="id_asc" />
          <el-option label="按误差从大到小" value="error_desc" />
          <el-option label="按误差从小到大" value="error_asc" />
        </el-select>
      </div>
      
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
            :class="{ 
              'is-selected': camera.image_id === selectedCameraId,
              'is-problem': isProblemCamera(camera),
              'is-good': isGoodCamera(camera)
            }"
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
              <div class="camera-item-error">
                <el-text size="small" :type="isProblemCamera(camera) ? 'primary' : (isGoodCamera(camera) ? 'success' : 'info')">
                  误差: {{ camera.mean_reprojection_error != null ? camera.mean_reprojection_error.toFixed(3) : '-' }} px
                </el-text>
              </div>
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
import { Search, QuestionFilled } from '@element-plus/icons-vue'
import { useCameraSelectionStore } from '@/stores/cameraSelection'
import type { CameraInfo } from '@/types'

const cameraSelectionStore = useCameraSelectionStore()

const cameras = computed(() => cameraSelectionStore.cameras)
const selectedCameraId = computed(() => cameraSelectionStore.selectedCameraId)
const errorThreshold = computed(() => cameraSelectionStore.errorThreshold)

const searchText = ref('')
const showOnlyProblemCamerasInList = ref(false)
const sortOrder = ref<'id_asc' | 'error_desc' | 'error_asc'>('id_asc')

// 问题相机：有误差数据且误差 > 阈值
function isProblemCamera(camera: CameraInfo): boolean {
  return camera.mean_reprojection_error != null && camera.mean_reprojection_error > errorThreshold.value
}

// 正常相机：有误差数据且误差 ≤ 阈值
function isGoodCamera(camera: CameraInfo): boolean {
  return camera.mean_reprojection_error != null && camera.mean_reprojection_error <= errorThreshold.value
}

const filteredCameras = computed(() => {
  let result = cameras.value
  
  // 搜索过滤
  if (searchText.value.trim()) {
    const query = searchText.value.toLowerCase().trim()
    result = result.filter(camera => {
      return (
        camera.image_id.toString().includes(query) ||
        camera.image_name.toLowerCase().includes(query)
      )
    })
  }
  
  // 问题相机筛选
  if (showOnlyProblemCamerasInList.value) {
    result = result.filter(camera => isProblemCamera(camera))
  }
  
  // 排序
  result = [...result].sort((a, b) => {
    if (sortOrder.value === 'id_asc') {
      return a.image_id - b.image_id
    } else if (sortOrder.value === 'error_desc') {
      const errA = a.mean_reprojection_error ?? -Infinity
      const errB = b.mean_reprojection_error ?? -Infinity
      return errB - errA // 从大到小
    } else if (sortOrder.value === 'error_asc') {
      const errA = a.mean_reprojection_error ?? Infinity
      const errB = b.mean_reprojection_error ?? Infinity
      return errA - errB // 从小到大
    }
    return 0
  })
  
  return result
})

function handleSelectCamera(cameraId: number) {
  cameraSelectionStore.setSelectedCamera(cameraId)
}

function handleFilterChange() {
  // 如果当前选中的相机被隐藏，清空选中
  if (showOnlyProblemCamerasInList.value && selectedCameraId.value !== null) {
    const selectedCamera = cameras.value.find(c => c.image_id === selectedCameraId.value)
    if (selectedCamera && !isProblemCamera(selectedCamera)) {
      cameraSelectionStore.setSelectedCamera(null)
    }
  }
}

function handleSortChange() {
  // 排序变化时不需要特殊处理
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

.controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
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

.camera-item.is-good {
  border-left: 4px solid #22c55e; /* 绿色 - 正常相机 */
}

.camera-item.is-good.is-selected {
  border-left: 4px solid #22c55e;
  border-color: #409eff;
}

.camera-item.is-problem {
  border-left: 4px solid #3b82f6; /* 蓝色 - 问题相机 */
}

.camera-item.is-problem.is-selected {
  border-left: 4px solid #3b82f6;
  border-color: #409eff;
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

.camera-item-error {
  margin-top: 4px;
}

.camera-item-position {
  margin-top: 4px;
}
</style>

