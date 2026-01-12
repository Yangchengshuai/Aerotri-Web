<template>
  <div class="brush-compare-viewer" ref="containerRef">
    <!-- Left panel -->
    <div
      class="viewer-panel left-panel"
      :style="{ width: `${dividerPosition}%` }"
    >
      <div class="panel-header left-header">
        <span class="label-badge">{{ leftLabel }}</span>
      </div>
      <div ref="leftCesiumContainer" class="cesium-container"></div>
    </div>

    <!-- Draggable divider -->
    <div
      class="divider"
      @mousedown="startDrag"
      @touchstart.prevent="startDrag"
    >
      <div class="divider-handle">
        <div class="divider-line"></div>
        <div class="divider-grip">⋮⋮</div>
        <div class="divider-line"></div>
      </div>
    </div>

    <!-- Right panel -->
    <div
      class="viewer-panel right-panel"
      :style="{ width: `${100 - dividerPosition}%` }"
    >
      <div class="panel-header right-header">
        <span class="label-badge">{{ rightLabel }}</span>
      </div>
      <div ref="rightCesiumContainer" class="cesium-container"></div>
    </div>

    <!-- Instructions -->
    <div class="instructions">
      <el-icon><InfoFilled /></el-icon>
      拖动分屏线对比两个版本
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <span>正在加载模型...</span>
    </div>

    <!-- Error state -->
    <div v-if="error" class="error-overlay">
      <el-alert :title="error" type="error" :closable="false" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { InfoFilled, Loading } from '@element-plus/icons-vue'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const props = withDefaults(defineProps<{
  leftTilesetUrl: string
  rightTilesetUrl: string
  leftLabel: string
  rightLabel: string
}>(), {})

const emit = defineEmits<{
  (e: 'left-loaded'): void
  (e: 'right-loaded'): void
  (e: 'error', error: string): void
}>()

// DOM refs
const containerRef = ref<HTMLElement | null>(null)
const leftCesiumContainer = ref<HTMLDivElement | null>(null)
const rightCesiumContainer = ref<HTMLDivElement | null>(null)

// State
const dividerPosition = ref(50) // 0-100 percentage
const loading = ref(true)
const error = ref<string | null>(null)
const isDragging = ref(false)

// Cesium viewers and tilesets
let leftViewer: Cesium.Viewer | null = null
let rightViewer: Cesium.Viewer | null = null
let leftTileset: Cesium.Cesium3DTileset | null = null
let rightTileset: Cesium.Cesium3DTileset | null = null
let isInitializing = false

// Camera sync state
let isSyncing = false
let leftCameraChangeListener: (() => void) | null = null
let rightCameraChangeListener: (() => void) | null = null
let syncAnimationFrame: number | null = null

// Set Cesium base URL
;(window as any).CESIUM_BASE_URL = '/cesium/'

// ==================== Initialization ====================

async function initViewer() {
  if (!leftCesiumContainer.value || !rightCesiumContainer.value || isInitializing) return
  isInitializing = true

  try {
    // Configure common viewer options
    const viewerOptions = {
      baseLayerPicker: false,
      vrButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      navigationHelpButton: false,
      animation: false,
      fullscreenButton: false,
    }

    // Create left viewer
    console.log('[BrushCompareViewer] Creating left viewer...')
    leftViewer = new Cesium.Viewer(leftCesiumContainer.value, viewerOptions)

    // Hide default credit
    const leftCreditContainer = leftViewer.cesiumWidget.creditContainer as HTMLElement
    if (leftCreditContainer) {
      leftCreditContainer.style.display = 'none'
    }

    // Configure left viewer for model-only viewing
    leftViewer.scene.globe.show = false
    leftViewer.imageryLayers.removeAll()
    leftViewer.scene.backgroundColor = Cesium.Color.BLACK.clone()

    // Enable free camera rotation
    leftViewer.camera.constrainedAxis = undefined
    leftViewer.camera.enableCollisionDetection = false

    // Create right viewer
    console.log('[BrushCompareViewer] Creating right viewer...')
    rightViewer = new Cesium.Viewer(rightCesiumContainer.value, viewerOptions)

    // Hide default credit
    const rightCreditContainer = rightViewer.cesiumWidget.creditContainer as HTMLElement
    if (rightCreditContainer) {
      rightCreditContainer.style.display = 'none'
    }

    // Configure right viewer for model-only viewing
    rightViewer.scene.globe.show = false
    rightViewer.imageryLayers.removeAll()
    rightViewer.scene.backgroundColor = Cesium.Color.BLACK.clone()

    // Enable free camera rotation
    rightViewer.camera.constrainedAxis = undefined
    rightViewer.camera.enableCollisionDetection = false

    // Setup camera sync
    setupCameraSync()

    // Load tilesets
    await loadTilesets()

    loading.value = false
  } catch (err: any) {
    console.error('[BrushCompareViewer] Init error:', err)
    error.value = `初始化失败: ${err.message}`
    loading.value = false
  } finally {
    isInitializing = false
  }
}

// ==================== Tileset Loading ====================

async function loadTilesets() {
  if (!leftViewer || !rightViewer) return

  try {
    // Load left tileset
    console.log('[BrushCompareViewer] Loading left tileset:', props.leftTilesetUrl)
    leftTileset = await Cesium.Cesium3DTileset.fromUrl(props.leftTilesetUrl)
    leftViewer.scene.primitives.add(leftTileset)
    emit('left-loaded')

    // Load right tileset
    console.log('[BrushCompareViewer] Loading right tileset:', props.rightTilesetUrl)
    rightTileset = await Cesium.Cesium3DTileset.fromUrl(props.rightTilesetUrl)
    rightViewer.scene.primitives.add(rightTileset)
    emit('right-loaded')

    // Wait for both tilesets to be ready
    await Promise.all([
      leftTileset.readyPromise,
      rightTileset.readyPromise,
    ])

    console.log('[BrushCompareViewer] Both tilesets loaded')

    // Zoom to model (use left viewer as reference)
    zoomToModel()
  } catch (err: any) {
    console.error('[BrushCompareViewer] Tileset load error:', err)
    error.value = `模型加载失败: ${err.message}`
    emit('error', err.message)
  }
}

function zoomToModel() {
  if (!leftViewer || !leftTileset) return

  // Use left tileset as reference
  const boundingSphere = leftTileset.boundingSphere
  if (!boundingSphere) return

  const center = boundingSphere.center
  const radius = boundingSphere.radius

  // Check if using local coordinates
  const centerMagnitude = Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z)
  const isLocalCoordinates = centerMagnitude < 1000

  if (isLocalCoordinates) {
    // Local coordinates - use lookAt
    const viewRange = radius * 2.5
    leftViewer.camera.lookAt(
      center,
      new Cesium.HeadingPitchRange(0, -0.5, viewRange)
    )

    // Sync right viewer to same position
    if (rightViewer) {
      rightViewer.camera.lookAt(
        center,
        new Cesium.HeadingPitchRange(0, -0.5, viewRange)
      )
    }
  } else {
    // Geographic coordinates - use viewBoundingSphere
    leftViewer.camera.viewBoundingSphere(
      boundingSphere,
      new Cesium.HeadingPitchRange(0, -0.5, radius * 2.5)
    )

    // Sync right viewer to same position
    if (rightViewer) {
      rightViewer.camera.viewBoundingSphere(
        boundingSphere,
        new Cesium.HeadingPitchRange(0, -0.5, radius * 2.5)
      )
    }
  }
}

// ==================== Viewport Management ====================

function updateViewports() {
  // Viewports are controlled by CSS width
  // Just trigger re-render if needed
  if (leftViewer) {
    leftViewer.scene.requestRender()
  }
  if (rightViewer) {
    rightViewer.scene.requestRender()
  }
}

// ==================== Camera Synchronization ====================

function setupCameraSync() {
  // Clean up existing listeners
  cleanupCameraSync()

  if (!leftViewer || !rightViewer) {
    return
  }

  console.log('[BrushCompareViewer] Setting up camera sync')

  // Use requestAnimationFrame for smooth sync
  leftCameraChangeListener = () => {
    if (!isSyncing) {
      scheduleSync('left')
    }
  }

  rightCameraChangeListener = () => {
    if (!isSyncing) {
      scheduleSync('right')
    }
  }

  // Listen to camera changed event for real-time sync
  leftViewer.camera.changed.addEventListener(leftCameraChangeListener)
  rightViewer.camera.changed.addEventListener(rightCameraChangeListener)
}

function cleanupCameraSync() {
  // Cancel any pending sync
  if (syncAnimationFrame !== null) {
    cancelAnimationFrame(syncAnimationFrame)
    syncAnimationFrame = null
  }

  if (leftViewer && leftCameraChangeListener) {
    leftViewer.camera.changed.removeEventListener(leftCameraChangeListener)
    leftCameraChangeListener = null
  }

  if (rightViewer && rightCameraChangeListener) {
    rightViewer.camera.changed.removeEventListener(rightCameraChangeListener)
    rightCameraChangeListener = null
  }
}

function scheduleSync(source: 'left' | 'right') {
  // Cancel any pending sync frame to avoid stacking
  if (syncAnimationFrame !== null) {
    cancelAnimationFrame(syncAnimationFrame)
  }

  // Schedule sync on next animation frame
  syncAnimationFrame = requestAnimationFrame(() => {
    syncCameraTo(source === 'left' ? 'right' : 'left')
    syncAnimationFrame = null
  })
}

function syncCameraTo(target: 'left' | 'right') {
  const sourceViewer = target === 'left' ? rightViewer : leftViewer
  const targetViewer = target === 'left' ? leftViewer : rightViewer

  if (!sourceViewer || !targetViewer) return

  isSyncing = true

  // Sync camera properties directly
  const camera = targetViewer.camera
  const sourceCamera = sourceViewer.camera

  // Clone properties and assign back
  camera.position = Cesium.Cartesian3.clone(sourceCamera.position)
  camera.direction = Cesium.Cartesian3.clone(sourceCamera.direction)
  camera.up = Cesium.Cartesian3.clone(sourceCamera.up)
  camera.right = Cesium.Cartesian3.clone(sourceCamera.right)

  // Sync frustum for consistent zoom
  camera.frustum = sourceCamera.frustum.clone()

  isSyncing = false
}

// ==================== Divider Drag ====================

function startDrag(e: MouseEvent | TouchEvent) {
  console.log('[BrushCompareViewer] Start drag')
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag)
  document.addEventListener('touchend', stopDrag)
}

function onDrag(e: MouseEvent | TouchEvent) {
  if (!isDragging.value || !containerRef.value) return

  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const rect = containerRef.value.getBoundingClientRect()
  const relativeX = clientX - rect.left
  const percentage = (relativeX / rect.width) * 100

  // Clamp between 5% and 95%
  dividerPosition.value = Math.max(5, Math.min(95, percentage))

  // Update shader uniforms for real-time feedback
  updateViewports()
}

function stopDrag() {
  console.log('[BrushCompareViewer] Stop drag, dividerPosition:', dividerPosition.value)
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// ==================== Lifecycle ====================

onMounted(() => {
  console.log('[BrushCompareViewer] onMounted')
  initViewer()
})

onUnmounted(() => {
  cleanupCameraSync()
  if (leftViewer) {
    leftViewer.destroy()
    leftViewer = null
  }
  if (rightViewer) {
    rightViewer.destroy()
    rightViewer = null
  }
})
</script>

<style scoped>
.brush-compare-viewer {
  display: flex;
  width: 100%;
  height: 600px;
  min-height: 500px;
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.viewer-panel {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  position: absolute;
  top: 12px;
  z-index: 10;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  pointer-events: none;
}

.left-header {
  left: 12px;
}

.right-header {
  right: 12px;
}

.cesium-container {
  flex: 1;
  width: 100%;
  height: 100%;
  position: relative;
}

.divider {
  width: 12px;
  height: 100%;
  background: #1a1a2e;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  z-index: 30;
  transition: background 0.2s;
  flex-shrink: 0;
}

.divider:hover {
  background: #2a2a3e;
}

.divider-handle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.divider-line {
  width: 2px;
  height: 30px;
  background: #404040;
  border-radius: 1px;
}

.divider-grip {
  color: #606060;
  font-size: 10px;
  letter-spacing: 2px;
}

.label-badge {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.instructions {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(64, 158, 255, 0.9);
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 40;
  pointer-events: none;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #909399;
  z-index: 200;
}

.error-overlay {
  padding: 20px;
}
</style>
