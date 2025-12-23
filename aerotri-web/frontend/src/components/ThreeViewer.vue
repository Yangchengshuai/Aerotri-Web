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
/**
 * ThreeViewer Component
 * 
 * This component renders 3D cameras and point clouds from COLMAP/GLOMAP reconstruction results.
 * 
 * Key features:
 * - Outlier camera filtering using IQR method to handle GPS-based global coordinates
 * - Dynamic camera size calculation based on valid camera distribution
 * - User-adjustable camera size multiplier (0.1x - 5.0x)
 * - Yellow camera frustums with adjustable thickness
 * - Robust error handling and canvas sizing for tab visibility changes
 * 
 * Note: Currently only loads camera data to reduce memory usage. Point cloud rendering
 * is reserved for future use (loadPoints function is intentionally unused).
 */
import { ref, onMounted, onUnmounted, watch, reactive, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Aim, Refresh, Loading, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { resultApi, partitionApi, blockApi } from '@/api'
import type { CameraInfo, Point3D } from '@/types'
import PartitionSelector from './PartitionSelector.vue'

const props = defineProps<{
  blockId: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const downloadingPly = ref(false)
const showCameras = ref(true)
const showPoints = ref(true)
const cameraSizeMultiplier = ref(1.0) // 用户可调节的相机大小倍数
let baseCameraScale = 0.2 // 基础相机尺寸（会根据场景自动计算）

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
const initError = ref<string | null>(null)

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

function handlePartitionChange(_partitionIndex: number | null) {
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

  // Renderer (guard WebGL context creation failures)
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.domElement.style.display = 'block'
    renderer.domElement.style.width = '100%'
    renderer.domElement.style.height = '100%'
    container.appendChild(renderer.domElement)
  } catch (err: any) {
    console.error('Failed to create WebGL renderer:', err)
    initError.value =
      '浏览器禁用或不支持 WebGL，无法渲染 3D 视图。请开启硬件加速或更换支持 WebGL 的浏览器/运行环境。'
    ElMessage.error(initError.value)
    return
  }

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
  if (!initialized) {
    // 如果 WebGL 初始化失败，提前终止并给出提示
    if (initError.value) {
      ElMessage.error(initError.value)
    }
    return
  }
  loading.value = true
  try {
    let camerasData: CameraInfo[] = []
    let numPointsTotal = 0

    // 只加载相机和统计信息，不再加载点云采样数据。
    try {
      if (isPartitioned.value && viewMode.value === 'partition' && selectedPartitionIndex.value !== null) {
        const [cameras, statsRes] = await Promise.all([
          partitionApi.getPartitionCameras(props.blockId, selectedPartitionIndex.value),
          partitionApi.getPartitionStats(props.blockId, selectedPartitionIndex.value),
        ])
        camerasData = cameras.data
        numPointsTotal = (statsRes.data as any).num_points3d ?? 0
      } else {
        const [cameras, statsRes] = await Promise.all([
          resultApi.getCameras(props.blockId),
          resultApi.getStats(props.blockId),
        ])
        camerasData = cameras.data
        numPointsTotal = (statsRes.data as any).num_points3d ?? 0
      }
    } catch (e) {
      console.error('Failed to load cameras/stats:', e)
      if (axios.isAxiosError(e)) {
        const status = e.response?.status
        const detail = (e.response?.data as any)?.detail
        const msg =
          e.code === 'ECONNABORTED'
            ? '加载相机/统计数据超时，请稍后重试（可检查网络/反向代理限制）'
            : status
              ? `加载相机/统计数据失败（HTTP ${status}${detail ? `: ${detail}` : ''}）`
              : `加载相机/统计数据失败${e.message ? `：${e.message}` : ''}`
        ElMessage.error(msg)
      } else {
        ElMessage.error('加载相机/统计数据失败，请稍后重试')
      }
      return
    }

    // 渲染相机；点云组清空（不请求点云）
    loadCameras(camerasData)
    pointsGroup.clear()

    stats.numCameras = camerasData.length
    stats.numPoints = numPointsTotal

    fitToView()
    // 触发一次尺寸校正（防止 tab 切换后 canvas 仍停留在 1x1）
    startEnsureCanvasSizedLoop()
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

  // Filter out outlier cameras using IQR (Interquartile Range) method
  // Compute distances from center for each axis
  const center = new THREE.Vector3()
  positions.forEach(p => center.add(p))
  center.divideScalar(positions.length)

  const distances: number[] = []
  positions.forEach(p => {
    distances.push(p.distanceTo(center))
  })

  // Sort distances to compute quartiles
  distances.sort((a, b) => a - b)
  const q1Idx = Math.floor(distances.length * 0.25)
  const q3Idx = Math.floor(distances.length * 0.75)
  const q1 = distances[q1Idx]
  const q3 = distances[q3Idx]
  const iqr = q3 - q1
  const lowerBound = q1 - 1.5 * iqr
  const upperBound = q3 + 1.5 * iqr

  // Filter valid cameras (within IQR bounds)
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
    // Fallback: use all cameras if filtering removes everything
    validCameras.push(...cameras)
    validPositions.push(...positions)
  }

  // Compute extent from valid cameras only
  let minX = Infinity, minY = Infinity, minZ = Infinity
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity
  validPositions.forEach(p => {
    if (p.x < minX) minX = p.x
    if (p.y < minY) minY = p.y
    if (p.z < minZ) minZ = p.z
    if (p.x > maxX) maxX = p.x
    if (p.y > maxY) maxY = p.y
    if (p.z > maxZ) maxZ = p.z
  })

  // Calculate scale based on valid cameras only
  let scale = 0.2 // Default fallback
  if (validPositions.length > 1) {
    // 1) Based on nearest neighbor distance (use smaller coefficient to avoid clustering)
    const p1 = validPositions[0]
    let minDist = Infinity
    // Check more neighbors for better estimation
    for (let i = 1; i < Math.min(validPositions.length, 50); i++) {
      const d = p1.distanceTo(validPositions[i])
      if (d > 0 && d < minDist) minDist = d
    }
    if (minDist !== Infinity) {
      scale = minDist * 0.15 // Reduced from 0.3 to 0.15 to make cameras smaller
    }

    // 2) Based on extent of valid cameras (use even smaller percentage)
    const extentX = maxX - minX
    const extentY = maxY - minY
    const extentZ = maxZ - minZ
    const maxExtent = Math.max(extentX, extentY, extentZ)
    if (Number.isFinite(maxExtent) && maxExtent > 0) {
      const extentBased = maxExtent * 0.001 // 约为有效场景尺寸的 0.1%（进一步减小）
      // Use the smaller of the two scales to avoid clustering
      if (extentBased < scale) {
        scale = extentBased
      }
    }
  }

  // Store base scale for user multiplier
  baseCameraScale = Math.max(0.01, scale)

  // Only render valid cameras (filter out outliers)
  // Note: validCameras and validPositions are already aligned by index from the filtering loop above
  validCameras.forEach((cam, validIdx) => {
    const frustum = createCameraFrustum(baseCameraScale)

    // Apply rotation from quaternion (COLMAP format: qw, qx, qy, qz)
    const quaternion = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
    frustum.quaternion.copy(quaternion)

    // Use precomputed position from validPositions (already aligned with validCameras)
    frustum.position.copy(validPositions[validIdx])

    // Apply initial user multiplier via scale
    frustum.scale.set(cameraSizeMultiplier.value, cameraSizeMultiplier.value, cameraSizeMultiplier.value)

    frustum.userData = { camera: cam, isOutlier: false }
    camerasGroup.add(frustum)
  })

  // Log filtering info for debugging
  if (cameras.length !== validCameras.length) {
    console.log(`Filtered ${cameras.length - validCameras.length} outlier cameras out of ${cameras.length} total`)
  }
}

function updateCameraSizes() {
  if (!camerasGroup || camerasGroup.children.length === 0) return
  
  // Simply scale all existing frustums using the multiplier
  const scaleFactor = cameraSizeMultiplier.value
  camerasGroup.children.forEach((child) => {
    if (child instanceof THREE.Group) {
      child.scale.set(scaleFactor, scaleFactor, scaleFactor)
    }
  })
}

// Reserved function for future point cloud rendering
// Currently not used as we only load camera data to reduce memory usage
// eslint-disable-next-line @typescript-eslint/no-unused-vars
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
  
  // 黄色加粗线条
  const material = new THREE.LineBasicMaterial({ 
    color: 0xffff00, // 黄色
    linewidth: 3, // 加粗（注意：linewidth 在某些渲染器可能不支持，但 Three.js 会尽量应用）
    opacity: 0.8, 
    transparent: true 
  })
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
