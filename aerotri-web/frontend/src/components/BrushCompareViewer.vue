<template>
  <div class="brush-compare-viewer" ref="containerRef">
    <!-- Single Cesium container -->
    <div ref="cesiumContainer" class="cesium-container"></div>

    <!-- Draggable divider line (visual only) -->
    <div
      class="divider-line"
      :style="{ left: `${dividerPosition}%` }"
      @mousedown="startDrag"
      @touchstart.prevent="startDrag"
    >
      <div class="divider-handle">⋮⋮</div>
    </div>

    <!-- Version labels -->
    <div class="version-labels">
      <div class="label left-label">
        <span class="label-badge">{{ leftLabel }}</span>
      </div>
      <div class="label right-label">
        <span class="label-badge">{{ rightLabel }}</span>
      </div>
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
import { ref, onMounted, onUnmounted } from 'vue'
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
const cesiumContainer = ref<HTMLDivElement | null>(null)

// State
const dividerPosition = ref(50) // 0-100 percentage
const loading = ref(true)
const error = ref<string | null>(null)
const isDragging = ref(false)

// Cesium viewer and tilesets (SINGLE viewer for true split-screen)
let viewer: Cesium.Viewer | null = null
let leftTileset: Cesium.Cesium3DTileset | null = null
let rightTileset: Cesium.Cesium3DTileset | null = null
let isInitializing = false

// Set Cesium base URL
;(window as any).CESIUM_BASE_URL = '/cesium/'

// ==================== Initialization ====================

async function initViewer() {
  if (!cesiumContainer.value || isInitializing) return
  isInitializing = true

  try {
    // Create SINGLE viewer
    console.log('[BrushCompareViewer] Creating viewer...')
    viewer = new Cesium.Viewer(cesiumContainer.value, {
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
    })

    // Hide default credit
    const creditContainer = viewer.cesiumWidget.creditContainer as HTMLElement
    if (creditContainer) {
      creditContainer.style.display = 'none'
    }

    // Configure for model-only viewing
    viewer.scene.globe.show = false
    viewer.imageryLayers.removeAll()
    viewer.scene.backgroundColor = Cesium.Color.BLACK.clone()

    // Enable free camera rotation
    viewer.camera.constrainedAxis = undefined
    viewer.camera.enableCollisionDetection = false

    // Set initial split position
    viewer.scene.splitPosition = dividerPosition.value / 100

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
  if (!viewer) return

  try {
    // Load left tileset with LEFT split direction
    console.log('[BrushCompareViewer] Loading left tileset:', props.leftTilesetUrl)
    leftTileset = await Cesium.Cesium3DTileset.fromUrl(props.leftTilesetUrl)

    // CRITICAL: Set splitDirection to LEFT - this tileset only renders on the left side
    leftTileset.splitDirection = Cesium.SplitDirection.LEFT

    viewer.scene.primitives.add(leftTileset)
    emit('left-loaded')

    // Load right tileset with RIGHT split direction
    console.log('[BrushCompareViewer] Loading right tileset:', props.rightTilesetUrl)
    rightTileset = await Cesium.Cesium3DTileset.fromUrl(props.rightTilesetUrl)

    // CRITICAL: Set splitDirection to RIGHT - this tileset only renders on the right side
    rightTileset.splitDirection = Cesium.SplitDirection.RIGHT

    viewer.scene.primitives.add(rightTileset)
    emit('right-loaded')

    // Wait for both tilesets to be ready
    await Promise.all([
      leftTileset.readyPromise,
      rightTileset.readyPromise,
    ])

    console.log('[BrushCompareViewer] Both tilesets loaded with splitDirection')

    // Zoom to fit both models
    zoomToModel()
  } catch (err: any) {
    console.error('[BrushCompareViewer] Tileset load error:', err)
    error.value = `模型加载失败: ${err.message}`
    emit('error', err.message)
  }
}

function zoomToModel() {
  if (!viewer || !leftTileset) return

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
    viewer.camera.lookAt(
      center,
      new Cesium.HeadingPitchRange(0, -0.5, viewRange)
    )
  } else {
    // Geographic coordinates - use viewBoundingSphere
    viewer.camera.viewBoundingSphere(
      boundingSphere,
      new Cesium.HeadingPitchRange(0, -0.5, radius * 2.5)
    )
  }
}

// ==================== Split Position Management ====================

function updateSplitPosition() {
  if (!viewer) return

  // Convert percentage (0-100) to normalized value (0.0-1.0)
  const normalizedPosition = dividerPosition.value / 100

  // Update Cesium's built-in split position
  viewer.scene.splitPosition = normalizedPosition

  // Request render to update the scene
  viewer.scene.requestRender()
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

  // Update Cesium split position in real-time
  updateSplitPosition()
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
  if (viewer) {
    viewer.destroy()
    viewer = null
  }
})
</script>

<style scoped>
.brush-compare-viewer {
  position: relative;
  width: 100%;
  height: 600px;
  min-height: 500px;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.cesium-container {
  width: 100%;
  height: 100%;
  position: relative;
}

/* Divider line - visual indicator only */
.divider-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.5);
  cursor: col-resize;
  z-index: 30;
  transition: background 0.2s;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.divider-line:hover {
  background: rgba(255, 255, 255, 0.8);
}

.divider-handle {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  padding: 8px 6px;
  border-radius: 4px;
  font-size: 10px;
  letter-spacing: 2px;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  pointer-events: none;
}

/* Version labels */
.version-labels {
  position: absolute;
  top: 12px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
  pointer-events: none;
  z-index: 20;
}

.label {
  pointer-events: none;
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
