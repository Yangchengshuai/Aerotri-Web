<template>
  <div class="three-viewer">
    <!-- Controls -->
    <div class="viewer-controls">
      <!-- View Mode Selector (for partitioned blocks) -->
      <div v-if="isPartitioned" class="mode-selector">
        <el-radio-group v-model="viewMode" size="small" @change="handleModeChange">
          <el-radio-button label="partition">单分区</el-radio-button>
          <el-radio-button label="merged" :disabled="!isMerged">合并结果</el-radio-button>
        </el-radio-group>
        
        <!-- Partition Selector (only in partition mode) -->
        <PartitionSelector
          v-if="viewMode === 'partition'"
          :block-id="blockId"
          v-model="selectedPartitionIndex"
          @change="handlePartitionChange"
          class="partition-selector-inline"
        />
      </div>
      
      <el-checkbox v-model="showCameras">显示相机</el-checkbox>
      <el-checkbox v-model="showPoints">显示点云</el-checkbox>
      <el-button size="small" @click="fitToView">
        <el-icon><Aim /></el-icon>
        居中
      </el-button>
      <el-button size="small" @click="loadData" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
      <el-button size="small" @click="downloadPly" :loading="downloadingPly">
        <el-icon><Download /></el-icon>
        下载完整点云
      </el-button>
    </div>

    <!-- 3D Canvas -->
    <div ref="containerRef" class="viewer-container"></div>

    <!-- Info Panel -->
    <div class="info-panel" v-if="stats">
      <div class="info-item">
        <span class="label">相机数</span>
        <span class="value">{{ stats.numCameras }}</span>
      </div>
      <div class="info-item">
        <span class="label">3D点数</span>
        <span class="value">{{ formatNumber(stats.numPoints) }}</span>
      </div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>加载中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, reactive, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Aim, Refresh, Loading, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { resultApi, partitionApi, blockApi } from '@/api'
import type { CameraInfo, Point3D, Block } from '@/types'
import PartitionSelector from './PartitionSelector.vue'

const props = defineProps<{
  blockId: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const downloadingPly = ref(false)
const showCameras = ref(true)
const showPoints = ref(true)

// Partition mode state
const viewMode = ref<'partition' | 'merged'>('merged')
const selectedPartitionIndex = ref<number | null>(null)
const isPartitioned = ref(false)
const isMerged = ref(false)

const stats = reactive({
  numCameras: 0,
  numPoints: 0,
})

// Three.js objects
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let camerasGroup: THREE.Group
let pointsGroup: THREE.Group
let animationId: number
let resizeObserver: ResizeObserver | null = null
let lastContainerWidth = 0
let lastContainerHeight = 0
let initialized = false
let ensureSizeRaf: number | null = null
let ensureSizeFrames = 0

onMounted(async () => {
  // ElementPlus tabs may mount while hidden -> container size can be 0.
  // Use nextTick + ResizeObserver to ensure correct canvas sizing.
  nextTick(() => {
    initThree()
  })
  
  // Check if block is partitioned and load data
  await checkPartitionStatus()
  await loadData()
})

async function checkPartitionStatus() {
  try {
    // Fetch block info directly
    const blockResponse = await blockApi.get(props.blockId)
    const block = blockResponse.data
    
    if (block?.partition_enabled) {
      isPartitioned.value = true
      
      // Check if merged
      isMerged.value = block.current_stage === 'completed'
      
      // Check partition status
      const response = await partitionApi.getStatus(props.blockId)
      const partitions = response.data.partitions || []
      const completedPartitions = partitions.filter((p: any) => p.status === 'COMPLETED')
      
      if (completedPartitions.length > 0 && !isMerged.value) {
        // If not merged, default to partition mode and select first completed partition
        viewMode.value = 'partition'
        selectedPartitionIndex.value = completedPartitions[0].index
      } else if (isMerged.value) {
        // If merged, default to merged mode
        viewMode.value = 'merged'
      } else if (completedPartitions.length > 0) {
        // Fallback: if partitions are completed but not merged, use partition mode
        viewMode.value = 'partition'
        selectedPartitionIndex.value = completedPartitions[0].index
      }
    }
  } catch (e) {
    console.error('Failed to check partition status:', e)
  }
}

function handleModeChange() {
  loadData()
}

function handlePartitionChange(partitionIndex: number | null) {
  if (viewMode.value === 'partition') {
    loadData()
  }
}

onUnmounted(() => {
  dispose()
})
// Tab 切换/后台切前台时，可能出现 canvas 尺寸没刷新导致渲染为空
const onVisibilityChange = () => {
  if (document.visibilityState === 'visible') {
    // 等一帧让布局稳定
    requestAnimationFrame(() => {
      try {
        onWindowResize()
        fitToView()
        startEnsureCanvasSizedLoop()
      } catch {
        // ignore
      }
    })
  }
}

document.addEventListener('visibilitychange', onVisibilityChange)

function initThree() {
  if (!containerRef.value) return

  const container = containerRef.value
  const rect = container.getBoundingClientRect()
  const width = Math.max(1, Math.floor(rect.width))
  const height = Math.max(1, Math.floor(rect.height))

  // Scene
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x202124) // Dark grey background

  // Camera
  camera = new THREE.PerspectiveCamera(60, width / height, 0.01, 100000)
  camera.position.set(10, 10, 10)
  camera.up.set(0, 1, 0) // Ensure Y is up

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.domElement.style.display = 'block'
  renderer.domElement.style.width = '100%'
  renderer.domElement.style.height = '100%'
  container.appendChild(renderer.domElement)

  // Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.enablePan = true
  controls.enableZoom = true
  controls.enableRotate = true
  controls.screenSpacePanning = true

  // Groups
  const rootGroup = new THREE.Group()
  // COLMAP uses Y-down, Z-forward. Three.js uses Y-up, Z-backward.
  // Rotate 180 deg around X to align them generally (though Z might be inverted relative to view)
  rootGroup.rotation.x = Math.PI 
  scene.add(rootGroup)

  camerasGroup = new THREE.Group()
  pointsGroup = new THREE.Group()
  rootGroup.add(camerasGroup)
  rootGroup.add(pointsGroup)

  // Axes helper
  const axesHelper = new THREE.AxesHelper(10)
  scene.add(axesHelper)

  // Grid helper
  const gridHelper = new THREE.GridHelper(100, 100, 0x444444, 0x222222)
  // Grid should be on the XZ plane, which is default. 
  // But since we rotated rootGroup, the "ground" for the data is inverted.
  // Let's keep grid at y=0.
  scene.add(gridHelper)

  // Start animation
  animate()

  // Handle resize
  window.addEventListener('resize', onWindowResize)

  // Observe container resize (more reliable than window resize)
  // Also handles tab visibility changes (when container goes from 0 to real size)
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect
      // If container just became visible (from 0 size), re-fit camera
      if (lastContainerWidth === 0 && lastContainerHeight === 0 && (width > 0 || height > 0)) {
        onWindowResize()
        // Delay fitToView to ensure data is loaded
        setTimeout(() => fitToView(), 100)
      } else if (width !== lastContainerWidth || height !== lastContainerHeight) {
        onWindowResize()
      }
      lastContainerWidth = width
      lastContainerHeight = height
    }
  })
  resizeObserver.observe(container)
  
  initialized = true

  // 某些浏览器/嵌入式 WebView 下，display:none -> display:block 时 ResizeObserver 可能不触发
  // 这里补一层轻量轮询，确保 canvas 从 1x1 正确变为真实尺寸，避免“黑屏但统计数字正常”
  startEnsureCanvasSizedLoop()
}

function animate() {
  animationId = requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

function onWindowResize() {
  if (!containerRef.value) return

  const rect = containerRef.value.getBoundingClientRect()
  const width = Math.max(1, Math.floor(rect.width))
  const height = Math.max(1, Math.floor(rect.height))

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.setSize(width, height)
}

function startEnsureCanvasSizedLoop() {
  // Run ~2 seconds at 60fps, or stop early once size is stable.
  if (ensureSizeRaf) return
  ensureSizeFrames = 0

  const tick = () => {
    ensureSizeFrames += 1
    ensureSizeRaf = requestAnimationFrame(tick)

    // Wait until three initialized
    if (!initialized || !containerRef.value || !renderer || !camera) return

    const rect = containerRef.value.getBoundingClientRect()
    const w = Math.max(1, Math.floor(rect.width))
    const h = Math.max(1, Math.floor(rect.height))

    // If still hidden (0x0 -> coerced to 1x1), keep waiting
    if (w <= 1 || h <= 1) return

    const size = renderer.getSize(new THREE.Vector2())
    const changed = Math.floor(size.x) !== w || Math.floor(size.y) !== h
    if (changed) {
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setPixelRatio(window.devicePixelRatio)
      renderer.setSize(w, h)
      // If data already loaded, try to fit once
      setTimeout(() => fitToView(), 0)
    }

    // Stop condition
    if (!changed && ensureSizeFrames > 20) {
      stopEnsureCanvasSizedLoop()
      return
    }
    if (ensureSizeFrames > 120) {
      stopEnsureCanvasSizedLoop()
      return
    }
  }

  ensureSizeRaf = requestAnimationFrame(tick)
}

function stopEnsureCanvasSizedLoop() {
  if (ensureSizeRaf) {
    cancelAnimationFrame(ensureSizeRaf)
    ensureSizeRaf = null
  }
}

async function loadData() {
  loading.value = true
  try {
    let camerasRes, pointsRes
    
    if (isPartitioned.value && viewMode.value === 'partition' && selectedPartitionIndex.value !== null) {
      // Load partition data
      const [cameras, points] = await Promise.all([
        partitionApi.getPartitionCameras(props.blockId, selectedPartitionIndex.value),
        partitionApi.getPartitionPoints(props.blockId, selectedPartitionIndex.value, 100000),
      ])
      
      camerasRes = { data: cameras.data }
      pointsRes = { data: { points: points.data.points, total: points.data.total } }
    } else {
      // Load merged data (or regular data for non-partitioned blocks)
      const [cameras, points] = await Promise.all([
        resultApi.getCameras(props.blockId),
        resultApi.getPoints(props.blockId, 100000),
      ])
      
      camerasRes = cameras
      pointsRes = points
    }

    loadCameras(camerasRes.data)
    loadPoints(pointsRes.data.points)

    stats.numCameras = camerasRes.data.length
    stats.numPoints = pointsRes.data.total

    fitToView()
    // 触发一次尺寸校正（防止 tab 切换后 canvas 仍停留在 1x1）
    startEnsureCanvasSizedLoop()
  } catch (e) {
    console.error('Failed to load data:', e)
    ElMessage.error('加载数据失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function downloadPly() {
  downloadingPly.value = true
  try {
    const response =
      isPartitioned.value && viewMode.value === 'partition' && selectedPartitionIndex.value !== null
        ? await partitionApi.downloadPartitionPoints3DPly(props.blockId, selectedPartitionIndex.value)
        : await resultApi.downloadPoints3DPly(props.blockId)
    // Create blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const suffix =
      isPartitioned.value && viewMode.value === 'partition' && selectedPartitionIndex.value !== null
        ? `_partition_${selectedPartitionIndex.value}`
        : ''
    link.setAttribute('download', `points3D_${props.blockId}${suffix}.ply`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('点云文件下载成功')
  } catch (e) {
    console.error('下载失败:', e)
    ElMessage.error('下载失败，请稍后重试')
  } finally {
    downloadingPly.value = false
  }
}

function loadCameras(cameras: CameraInfo[]) {
  camerasGroup.clear()

  // Calculate average distance between cameras to guess scene scale
  // for appropriately sizing camera frustums
  let scale = 0.2 // Default fallback
  if (cameras.length > 1) {
      const getPos = (cam: CameraInfo) => {
          const q = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
          const rot = new THREE.Matrix4().makeRotationFromQuaternion(q)
          const pos = new THREE.Vector3(-cam.tx, -cam.ty, -cam.tz)
          pos.applyMatrix4(rot.transpose())
          return pos
      }
      
      const p1 = getPos(cameras[0])
      // Find the closest neighbor to camera 0 to avoid using a far-away camera
      let minDist = Infinity
      
      // Check first 10 cameras
      for(let i=1; i < Math.min(cameras.length, 10); i++) {
          const p2 = getPos(cameras[i])
          const d = p1.distanceTo(p2)
          if (d > 0 && d < minDist) minDist = d
      }
      
      if (minDist !== Infinity) {
          scale = minDist * 0.3 // Camera frustum size approx 1/3 of inter-camera distance
      }
      // Clamp scale to reasonable bounds [0.01, 5.0]
      scale = Math.max(0.01, Math.min(scale, 5.0))
  }

  cameras.forEach((cam) => {
    const frustum = createCameraFrustum(scale)
    
    // Apply rotation from quaternion
    const quaternion = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
    frustum.quaternion.copy(quaternion)
    
    // Calculate camera position: C = -R^T * t
    const rotation = new THREE.Matrix4().makeRotationFromQuaternion(quaternion)
    const position = new THREE.Vector3(-cam.tx, -cam.ty, -cam.tz)
    position.applyMatrix4(rotation.transpose())
    frustum.position.copy(position)

    frustum.userData = { camera: cam }
    camerasGroup.add(frustum)
  })
}

function loadPoints(points: Point3D[]) {
  pointsGroup.clear()

  if (points.length === 0) return

  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(points.length * 3)
  const colors = new Float32Array(points.length * 3)

  points.forEach((point, i) => {
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
  pointsGroup.add(pointsMesh)
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
  
  const material = new THREE.LineBasicMaterial({ color: 0xff3333, opacity: 0.5, transparent: true })
  const lines = new THREE.LineSegments(geometry, material)
  group.add(lines)
  
  return group
}

function fitToView() {
  const box = new THREE.Box3()
  
  if (camerasGroup.children.length > 0) {
    box.expandByObject(camerasGroup)
  }
  if (pointsGroup.children.length > 0) {
    box.expandByObject(pointsGroup)
  }
  
  if (box.isEmpty()) return

  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  const radius = Math.max(1e-6, maxDim * 0.5)

  // Set near/far to avoid clipping on very small/large scenes
  camera.near = Math.max(0.001, radius / 1000)
  camera.far = Math.max(1000, radius * 500)
  camera.updateProjectionMatrix()

  // Place camera at a reasonable distance along a diagonal direction
  const fov = (camera.fov * Math.PI) / 180
  const dist = radius / Math.sin(fov / 2)
  const dir = new THREE.Vector3(1, 1, 1).normalize()
  camera.position.copy(center.clone().add(dir.multiplyScalar(dist)))

  controls.target.copy(center)
  controls.update()
}

function dispose() {
  stopEnsureCanvasSizedLoop()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  
  window.removeEventListener('resize', onWindowResize)
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
    resizeObserver.disconnect()
    resizeObserver = null
  }
  
  if (renderer && containerRef.value) {
    containerRef.value.removeChild(renderer.domElement)
    renderer.dispose()
  }
}

// Watch visibility toggles
watch(showCameras, (visible) => {
  if (camerasGroup) camerasGroup.visible = visible
})

watch(showPoints, (visible) => {
  if (pointsGroup) pointsGroup.visible = visible
})

function formatNumber(num: number): string {
  return num.toLocaleString()
}
</script>

<style scoped>
.three-viewer {
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

.mode-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 4px;
}

.partition-selector-inline {
  margin-left: 8px;
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
