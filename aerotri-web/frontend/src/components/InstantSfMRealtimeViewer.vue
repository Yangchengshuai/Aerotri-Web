<template>
  <div class="realtime-viewer">
    <!-- Controls -->
    <div class="viewer-controls">
      <el-checkbox v-model="showCameras">显示相机</el-checkbox>
      <el-checkbox v-model="showPoints">显示点云</el-checkbox>
      <div v-if="showCameras" class="camera-size-control">
        <span class="control-label">相机大小</span>
        <el-slider
          v-model="cameraSizeMultiplier"
          :min="0.1"
          :max="5.0"
          :step="0.1"
          :show-tooltip="true"
          :format-tooltip="(val: number) => `${val.toFixed(1)}x`"
          @change="updateCameraSizes"
          style="width: 120px;"
        />
      </div>
      <el-button size="small" @click="fitToView">
        <el-icon><Aim /></el-icon>
        居中
      </el-button>
      <el-button size="small" @click="reconnect" :loading="!connected">
        <el-icon><Refresh /></el-icon>
        {{ connected ? '已连接' : '重连' }}
      </el-button>
    </div>

    <!-- 3D Canvas -->
    <div ref="containerRef" class="viewer-container"></div>

    <!-- Info Panel -->
    <div class="info-panel">
      <div class="info-item">
        <span class="label">优化阶段</span>
        <span class="value">{{ currentStepName || '等待数据...' }}</span>
      </div>
      <div class="info-item">
        <span class="label">步骤</span>
        <span class="value">{{ currentStep }}</span>
      </div>
      <div class="info-item">
        <span class="label">相机数</span>
        <span class="value">{{ stats.numCameras }}</span>
      </div>
      <div class="info-item">
        <span class="label">3D点数</span>
        <span class="value">{{ formatNumber(stats.numPoints) }}</span>
      </div>
      <div class="info-item" v-if="!connected">
        <span class="label">连接状态</span>
        <span class="value" style="color: #f56c6c">未连接</span>
      </div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="!initialized" class="loading-overlay">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>初始化中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, reactive, nextTick, computed } from 'vue'
import * as THREE from 'three'
import { Aim, Refresh, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useInstantsfmVisualization } from '@/composables/useInstantsfmVisualization'
import { useThreeScene } from '@/composables/useThreeScene'
import type { CameraInfo, Point3D } from '@/types'

const props = defineProps<{
  blockId: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const showCameras = ref(true)
const showPoints = ref(true)
const cameraSizeMultiplier = ref(1.0)
let baseCameraScale = 0.2

// Three.js scene setup
const {
  scene,
  camera,
  renderer,
  controls,
  camerasGroup,
  pointsGroup,
  initialized,
  initError,
  initThree,
  fitToView,
  dispose,
} = useThreeScene(containerRef, (error) => {
  ElMessage.error(error)
})

// Real-time visualization
const { connected, update, error, connect, disconnect } = useInstantsfmVisualization(props.blockId)

const currentStep = computed(() => update.value?.step ?? 0)
const currentStepName = computed(() => update.value?.stepName ?? '')

const stats = reactive({
  numCameras: 0,
  numPoints: 0,
})

onMounted(async () => {
  nextTick(() => {
    initThree()
  })
  
  // Connect to visualization WebSocket
  connect()
})

onUnmounted(() => {
  disconnect()
  dispose()
})

// Watch for updates and update scene
watch(update, (newUpdate) => {
  if (!newUpdate || !initialized.value) return
  
  // Update cameras
  if (newUpdate.cameras && camerasGroup.value) {
    loadCameras(newUpdate.cameras)
  }
  
  // Update points
  if (newUpdate.points && pointsGroup.value) {
    loadPoints(newUpdate.points)
  }
  
  // Update stats
  stats.numCameras = newUpdate.cameras?.length ?? 0
  stats.numPoints = newUpdate.points?.length ?? 0
}, { immediate: true })

// Watch for connection errors
watch(error, (newError) => {
  if (newError) {
    ElMessage.warning(`可视化连接错误: ${newError}`)
  }
})

function reconnect() {
  disconnect()
  setTimeout(() => {
    connect()
  }, 500)
}

function loadCameras(cameras: CameraInfo[]) {
  if (!camerasGroup.value) return
  camerasGroup.value.clear()

  if (cameras.length === 0) return

  // Pre-compute all camera positions
  const positions: THREE.Vector3[] = []
  const getPos = (cam: CameraInfo) => {
    const q = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
    const rot = new THREE.Matrix4().makeRotationFromQuaternion(q)
    const pos = new THREE.Vector3(-cam.tx, -cam.ty, -cam.tz)
    pos.applyMatrix4(rot.transpose())
    return pos
  }

  cameras.forEach((cam) => {
    const p = getPos(cam)
    positions.push(p)
  })

  // Filter out outlier cameras using IQR method
  const center = new THREE.Vector3()
  positions.forEach(p => center.add(p))
  center.divideScalar(positions.length)

  const distances: number[] = []
  positions.forEach(p => {
    distances.push(p.distanceTo(center))
  })

  distances.sort((a, b) => a - b)
  const q1Idx = Math.floor(distances.length * 0.25)
  const q3Idx = Math.floor(distances.length * 0.75)
  const q1 = distances[q1Idx]
  const q3 = distances[q3Idx]
  const iqr = q3 - q1
  const lowerBound = q1 - 1.5 * iqr
  const upperBound = q3 + 1.5 * iqr

  const validCameras: CameraInfo[] = []
  const validPositions: THREE.Vector3[] = []
  cameras.forEach((cam, idx) => {
    const dist = distances[idx]
    if (dist >= lowerBound && dist <= upperBound) {
      validCameras.push(cam)
      validPositions.push(positions[idx])
    }
  })

  if (validCameras.length === 0) {
    validCameras.push(...cameras)
    validPositions.push(...positions)
  }

  // Calculate scale
  let scale = 0.2
  if (validPositions.length > 1) {
    const p1 = validPositions[0]
    let minDist = Infinity
    for (let i = 1; i < Math.min(validPositions.length, 50); i++) {
      const d = p1.distanceTo(validPositions[i])
      if (d > 0 && d < minDist) minDist = d
    }
    if (minDist !== Infinity) {
      scale = minDist * 0.15
    }
  }

  baseCameraScale = Math.max(0.01, scale)

  // Render cameras
  validCameras.forEach((cam, validIdx) => {
    const frustum = createCameraFrustum(baseCameraScale)
    const quaternion = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
    frustum.quaternion.copy(quaternion)
    frustum.position.copy(validPositions[validIdx])
    frustum.scale.set(cameraSizeMultiplier.value, cameraSizeMultiplier.value, cameraSizeMultiplier.value)
    camerasGroup.value!.add(frustum)
  })
}

function loadPoints(points: Point3D[]) {
  if (!pointsGroup.value) return
  
  // For performance, sample points if there are too many
  const maxPoints = 100000
  const sampledPoints = points.length > maxPoints 
    ? points.filter((_, i) => i % Math.ceil(points.length / maxPoints) === 0)
    : points

  pointsGroup.value.clear()

  if (sampledPoints.length === 0) return

  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(sampledPoints.length * 3)
  const colors = new Float32Array(sampledPoints.length * 3)

  sampledPoints.forEach((point, i) => {
    positions[i * 3] = point.x
    positions[i * 3 + 1] = point.y
    positions[i * 3 + 2] = point.z

    colors[i * 3] = point.r / 255
    colors[i * 3 + 1] = point.g / 255
    colors[i * 3 + 2] = point.b / 255
  })

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

  const material = new THREE.PointsMaterial({
    size: 0.05,
    vertexColors: true,
    sizeAttenuation: true,
  })

  const pointsMesh = new THREE.Points(geometry, material)
  pointsGroup.value.add(pointsMesh)
}

function createCameraFrustum(scale: number = 0.3): THREE.Object3D {
  const group = new THREE.Group()
  
  const w = scale
  const h = scale * 0.75
  const d = scale * 1.5
  
  const points = [
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(-w, -h, d),
    new THREE.Vector3(w, -h, d),
    new THREE.Vector3(w, h, d),
    new THREE.Vector3(-w, h, d),
  ]
  
  const geometry = new THREE.BufferGeometry()
  const positions = [
    ...points[0].toArray(), ...points[1].toArray(),
    ...points[0].toArray(), ...points[2].toArray(),
    ...points[0].toArray(), ...points[3].toArray(),
    ...points[0].toArray(), ...points[4].toArray(),
    ...points[1].toArray(), ...points[2].toArray(),
    ...points[2].toArray(), ...points[3].toArray(),
    ...points[3].toArray(), ...points[4].toArray(),
    ...points[4].toArray(), ...points[1].toArray(),
  ]
  
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  
  const material = new THREE.LineBasicMaterial({ 
    color: 0xffff00,
    linewidth: 3,
    opacity: 0.8, 
    transparent: true 
  })
  const lines = new THREE.LineSegments(geometry, material)
  group.add(lines)
  
  return group
}

function updateCameraSizes() {
  if (!camerasGroup.value || camerasGroup.value.children.length === 0) return
  
  const scaleFactor = cameraSizeMultiplier.value
  camerasGroup.value.children.forEach((child) => {
    if (child instanceof THREE.Group) {
      child.scale.set(scaleFactor, scaleFactor, scaleFactor)
    }
  })
}

watch(showCameras, (visible) => {
  if (camerasGroup.value) camerasGroup.value.visible = visible
})

watch(showPoints, (visible) => {
  if (pointsGroup.value) pointsGroup.value.visible = visible
})

function formatNumber(num: number): string {
  return num.toLocaleString()
}
</script>

<style scoped>
.realtime-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
}

.viewer-controls {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 6px;
}

.camera-size-control {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.control-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

.viewer-container {
  flex: 1;
  width: 100%;
}

.info-panel {
  position: absolute;
  bottom: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 6px;
  color: white;
}

.info-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.info-item .label {
  font-size: 11px;
  color: #aaa;
}

.info-item .value {
  font-size: 16px;
  font-weight: 600;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(26, 26, 46, 0.8);
  color: white;
  z-index: 20;
}
</style>





