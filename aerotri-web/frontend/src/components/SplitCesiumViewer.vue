<template>
  <div class="split-cesium-viewer" ref="containerRef">
    <!-- Left Panel -->
    <div
      class="viewer-panel left-panel"
      :style="{ width: `${splitPosition}%` }"
    >
      <div class="panel-header" v-if="leftLabel">
        <span>{{ leftLabel }}</span>
      </div>
      <div class="cesium-container">
        <CesiumViewer
          :tileset-url="leftTilesetUrl"
          :key="leftTilesetUrl"
          @viewer-ready="onLeftViewerReady"
        />
      </div>
    </div>

    <!-- Draggable Divider -->
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

    <!-- Right Panel -->
    <div
      class="viewer-panel right-panel"
      :style="{ width: `${100 - splitPosition}%` }"
    >
      <div class="panel-header" v-if="rightLabel">
        <span>{{ rightLabel }}</span>
      </div>
      <div class="cesium-container">
        <CesiumViewer
          :tileset-url="rightTilesetUrl"
          :key="rightTilesetUrl"
          @viewer-ready="onRightViewerReady"
        />
      </div>
    </div>

    <!-- Sync indicator -->
    <div class="sync-badge" v-if="syncCamera">
      <el-icon><Link /></el-icon>
      视角同步
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import * as Cesium from 'cesium'
import { Link } from '@element-plus/icons-vue'
import CesiumViewer from './CesiumViewer.vue'

const props = withDefaults(defineProps<{
  leftTilesetUrl: string
  rightTilesetUrl: string
  leftLabel?: string
  rightLabel?: string
  syncCamera?: boolean
  initialSplit?: number
}>(), {
  syncCamera: false,
  initialSplit: 50,
})

const emit = defineEmits<{
  (e: 'left-loaded'): void
  (e: 'right-loaded'): void
}>()

// DOM refs
const containerRef = ref<HTMLElement | null>(null)

// State
const splitPosition = ref(props.initialSplit)
const isDragging = ref(false)

// Viewer instances
let leftViewer: Cesium.Viewer | null = null
let rightViewer: Cesium.Viewer | null = null

// Sync state
let isSyncing = false
let leftCameraChangeListener: (() => void) | null = null
let rightCameraChangeListener: (() => void) | null = null
let syncAnimationFrame: number | null = null

// ==================== Viewer Ready Callbacks ====================

function onLeftViewerReady(viewer: Cesium.Viewer) {
  console.log('[SplitCesiumViewer] Left viewer ready')
  leftViewer = viewer
  emit('left-loaded')
  setupCameraSync()
}

function onRightViewerReady(viewer: Cesium.Viewer) {
  console.log('[SplitCesiumViewer] Right viewer ready')
  rightViewer = viewer
  emit('right-loaded')
  setupCameraSync()
}

// ==================== Camera Synchronization ====================

function setupCameraSync() {
  // Clean up existing listeners
  cleanupCameraSync()

  if (!props.syncCamera || !leftViewer || !rightViewer) {
    return
  }

  console.log('[SplitCesiumViewer] Setting up camera sync')

  // Use requestAnimationFrame for smooth sync
  leftCameraChangeListener = () => {
    if (!isSyncing && props.syncCamera) {
      scheduleSync('left')
    }
  }

  rightCameraChangeListener = () => {
    if (!isSyncing && props.syncCamera) {
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
  if (!props.syncCamera) return

  const sourceViewer = target === 'left' ? rightViewer : leftViewer
  const targetViewer = target === 'left' ? leftViewer : rightViewer

  if (!sourceViewer || !targetViewer) return

  isSyncing = true

  // Sync camera properties directly
  const camera = targetViewer.camera
  const sourceCamera = sourceViewer.camera

  // Clone properties and assign back (Cesium uses clone() not copy())
  camera.position = Cesium.Cartesian3.clone(sourceCamera.position)
  camera.direction = Cesium.Cartesian3.clone(sourceCamera.direction)
  camera.up = Cesium.Cartesian3.clone(sourceCamera.up)
  camera.right = Cesium.Cartesian3.clone(sourceCamera.right)

  // Sync frustum for consistent zoom
  camera.frustum = sourceCamera.frustum.clone()

  isSyncing = false
}

// Watch for sync camera changes
watch(
  () => props.syncCamera,
  (enabled) => {
    console.log('[SplitCesiumViewer] Sync camera changed to:', enabled)
    if (enabled) {
      setupCameraSync()
    } else {
      cleanupCameraSync()
    }
  }
)

// ==================== Divider Drag ====================

function startDrag(e: MouseEvent | TouchEvent) {
  console.log('[SplitCesiumViewer] Start drag')
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

  // Clamp between 20% and 80%
  splitPosition.value = Math.max(20, Math.min(80, percentage))
}

function stopDrag() {
  console.log('[SplitCesiumViewer] Stop drag, splitPosition:', splitPosition.value)
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// ==================== Lifecycle ====================

onUnmounted(() => {
  cleanupCameraSync()
})
</script>

<style scoped>
.split-cesium-viewer {
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
  left: 12px;
  z-index: 10;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  pointer-events: none;
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

.sync-badge {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(64, 158, 255, 0.9);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 40;
}
</style>
