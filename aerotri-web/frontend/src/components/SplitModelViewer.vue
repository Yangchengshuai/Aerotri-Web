<template>
  <div class="split-model-viewer" ref="containerRef">
    <!-- Left Panel -->
    <div 
      class="viewer-panel left-panel" 
      :style="{ width: `${splitPosition}%` }"
    >
      <div class="panel-header" v-if="leftLabel">
        <span>{{ leftLabel }}</span>
      </div>
      <div ref="leftCanvasRef" class="canvas-container"></div>
      <div v-if="leftLoading" class="loading-overlay">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>加载中...</span>
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
      <div ref="rightCanvasRef" class="canvas-container"></div>
      <div v-if="rightLoading" class="loading-overlay">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>加载中...</span>
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
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { Loading, Link } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  leftUrl?: string
  rightUrl?: string
  leftLabel?: string
  rightLabel?: string
  syncCamera?: boolean
  initialSplit?: number
}>(), {
  syncCamera: true,
  initialSplit: 50,
})

const emit = defineEmits<{
  (e: 'left-loaded'): void
  (e: 'right-loaded'): void
  (e: 'left-error', error: Error): void
  (e: 'right-error', error: Error): void
}>()

// DOM refs
const containerRef = ref<HTMLElement | null>(null)
const leftCanvasRef = ref<HTMLElement | null>(null)
const rightCanvasRef = ref<HTMLElement | null>(null)

// State
const splitPosition = ref(props.initialSplit)
const leftLoading = ref(false)
const rightLoading = ref(false)
const isDragging = ref(false)

// Pending URLs for when scene is not yet initialized
let pendingLeftUrl: string | null = null
let pendingRightUrl: string | null = null

// Three.js instances
let leftRenderer: THREE.WebGLRenderer | null = null
let leftScene: THREE.Scene | null = null
let leftCamera: THREE.PerspectiveCamera | null = null
let leftControls: OrbitControls | null = null
let leftAnimationId: number | null = null

let rightRenderer: THREE.WebGLRenderer | null = null
let rightScene: THREE.Scene | null = null
let rightCamera: THREE.PerspectiveCamera | null = null
let rightControls: OrbitControls | null = null
let rightAnimationId: number | null = null

// Sync state
let isSyncing = false

// ==================== Three.js Setup ====================

function initScene(
  canvasRef: HTMLElement,
  side: 'left' | 'right'
): {
  renderer: THREE.WebGLRenderer
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  controls: OrbitControls
} {
  const width = canvasRef.clientWidth
  const height = canvasRef.clientHeight || 400

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a2e)

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
  camera.position.set(0, 0, 5)

  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  canvasRef.innerHTML = ''
  canvasRef.appendChild(renderer.domElement)

  // Lighting
  const dirLight = new THREE.DirectionalLight(0xffffff, 1)
  dirLight.position.set(1, 1, 1)
  scene.add(dirLight)
  scene.add(new THREE.AmbientLight(0xffffff, 0.4))

  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // Setup sync events
  if (props.syncCamera) {
    controls.addEventListener('change', () => {
      if (!isSyncing) {
        syncCameraToOther(side)
      }
    })
  }

  return { renderer, scene, camera, controls }
}

function syncCameraToOther(source: 'left' | 'right') {
  if (!props.syncCamera) return
  
  const sourceCamera = source === 'left' ? leftCamera : rightCamera
  const sourceControls = source === 'left' ? leftControls : rightControls
  const targetCamera = source === 'left' ? rightCamera : leftCamera
  const targetControls = source === 'left' ? rightControls : leftControls

  if (!sourceCamera || !sourceControls || !targetCamera || !targetControls) return

  isSyncing = true

  // Sync camera position and orientation
  targetCamera.position.copy(sourceCamera.position)
  targetCamera.quaternion.copy(sourceCamera.quaternion)
  targetControls.target.copy(sourceControls.target)
  targetControls.update()

  isSyncing = false
}

function fitCameraToObject(
  object: THREE.Object3D,
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls
) {
  const box = new THREE.Box3().setFromObject(object)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())

  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = (camera.fov * Math.PI) / 180
  let cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2)))
  cameraZ *= 1.5

  camera.position.set(center.x, center.y, center.z + cameraZ)
  camera.lookAt(center)
  controls.target.copy(center)
  controls.update()
}

async function loadModel(
  url: string,
  scene: THREE.Scene,
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  setLoading: (v: boolean) => void
): Promise<THREE.Object3D> {
  setLoading(true)
  console.log('[SplitModelViewer] Loading model:', url)

  // Remove existing meshes
  const toRemove = scene.children.filter(c => !(c instanceof THREE.Light))
  toRemove.forEach(c => scene.remove(c))

  return new Promise((resolve, reject) => {
    const urlLower = url.toLowerCase()

    if (urlLower.endsWith('.ply')) {
      const loader = new PLYLoader()
      loader.load(
        url,
        (geometry) => {
          geometry.computeVertexNormals()
          const material = new THREE.MeshStandardMaterial({
            color: 0xcccccc,
            flatShading: false,
            metalness: 0.1,
            roughness: 0.8,
            vertexColors: !!geometry.getAttribute('color'),
          })
          const mesh = new THREE.Mesh(geometry, material)
          scene.add(mesh)
          fitCameraToObject(mesh, camera, controls)
          setLoading(false)
          resolve(mesh)
        },
        undefined,
        (error) => {
          setLoading(false)
          reject(error)
        }
      )
    } else if (urlLower.endsWith('.obj')) {
      // Check for MTL file
      const mtlUrl = url.replace(/\.obj$/i, '.mtl')
      const baseUrl = url.substring(0, url.lastIndexOf('/') + 1)

      console.log('[SplitModelViewer] Loading OBJ:', url)
      console.log('[SplitModelViewer] MTL URL:', mtlUrl)
      console.log('[SplitModelViewer] Base URL for materials:', baseUrl)

      const mtlLoader = new MTLLoader()
      mtlLoader.setPath(baseUrl)

      // Try to load MTL first
      const mtlFileName = mtlUrl.substring(mtlUrl.lastIndexOf('/') + 1)
      console.log('[SplitModelViewer] MTL filename:', mtlFileName)

      mtlLoader.load(
        mtlFileName,
        (materials) => {
          console.log('[SplitModelViewer] MTL loaded successfully, materials:', materials)
          materials.preload()
          const objLoader = new OBJLoader()
          objLoader.setMaterials(materials)
          objLoader.load(
            url,
            (object) => {
              console.log('[SplitModelViewer] OBJ loaded successfully, object:', object)
              console.log('[SplitModelViewer] Object children count:', object.children.length)

              // Log details about each child
              object.traverse((child) => {
                if (child instanceof THREE.Mesh) {
                  console.log('[SplitModelViewer] Mesh found:', {
                    name: child.name,
                    geometry: child.geometry.type,
                    vertices: child.geometry.attributes.position?.count,
                    material: child.material?.type,
                  })
                }
              })

              scene.add(object)
              console.log('[SplitModelViewer] Object added to scene, scene children:', scene.children.length)

              fitCameraToObject(object, camera, controls)
              console.log('[SplitModelViewer] Camera fitted to object')

              setLoading(false)
              resolve(object)
            },
            (xhr) => {
              if (xhr.lengthComputable) {
                const percentComplete = (xhr.loaded / xhr.total) * 100
                console.log('[SplitModelViewer] OBJ load progress:', percentComplete.toFixed(2) + '%')
              }
            },
            (error) => {
              console.error('[SplitModelViewer] OBJ load error:', error)
              setLoading(false)
              reject(error)
            }
          )
        },
        (xhr) => {
          if (xhr.lengthComputable) {
            const percentComplete = (xhr.loaded / xhr.total) * 100
            console.log('[SplitModelViewer] MTL load progress:', percentComplete.toFixed(2) + '%')
          }
        },
        (error) => {
          console.warn('[SplitModelViewer] MTL not found or failed to load, loading OBJ without materials')
          console.log('[SplitModelViewer] MTL error:', error)
          // MTL not found, load OBJ without materials
          const objLoader = new OBJLoader()
          objLoader.load(
            url,
            (object) => {
              console.log('[SplitModelViewer] OBJ loaded (without MTL), object:', object)
              // Apply default material
              object.traverse((child) => {
                if (child instanceof THREE.Mesh) {
                  child.material = new THREE.MeshStandardMaterial({
                    color: 0xcccccc,
                    metalness: 0.1,
                    roughness: 0.8,
                  })
                  console.log('[SplitModelViewer] Applied default material to mesh')
                }
              })
              scene.add(object)
              console.log('[SplitModelViewer] Object added to scene')
              fitCameraToObject(object, camera, controls)
              setLoading(false)
              resolve(object)
            },
            (xhr) => {
              if (xhr.lengthComputable) {
                const percentComplete = (xhr.loaded / xhr.total) * 100
                console.log('[SplitModelViewer] OBJ load progress (no MTL):', percentComplete.toFixed(2) + '%')
              }
            },
            (error) => {
              console.error('[SplitModelViewer] OBJ load error (no MTL):', error)
              setLoading(false)
              reject(error)
            }
          )
        }
      )
    } else {
      setLoading(false)
      reject(new Error(`Unsupported file format: ${url}`))
    }
  })
}

// ==================== Animation Loop ====================

function startLeftAnimation() {
  if (leftAnimationId !== null) return

  function animate() {
    leftAnimationId = requestAnimationFrame(animate)
    if (leftControls) leftControls.update()
    if (leftRenderer && leftScene && leftCamera) {
      leftRenderer.render(leftScene, leftCamera)
    }
  }
  animate()
}

function startRightAnimation() {
  if (rightAnimationId !== null) return

  function animate() {
    rightAnimationId = requestAnimationFrame(animate)
    if (rightControls) rightControls.update()
    if (rightRenderer && rightScene && rightCamera) {
      rightRenderer.render(rightScene, rightCamera)
    }
  }
  animate()
}

function stopLeftAnimation() {
  if (leftAnimationId !== null) {
    cancelAnimationFrame(leftAnimationId)
    leftAnimationId = null
  }
}

function stopRightAnimation() {
  if (rightAnimationId !== null) {
    cancelAnimationFrame(rightAnimationId)
    rightAnimationId = null
  }
}

// ==================== Divider Drag ====================

function startDrag(e: MouseEvent | TouchEvent) {
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

  // Resize renderers
  handleResize()
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// ==================== Resize Handling ====================

function handleResize() {
  nextTick(() => {
    if (leftCanvasRef.value && leftCamera && leftRenderer) {
      const width = leftCanvasRef.value.clientWidth
      const height = leftCanvasRef.value.clientHeight || 400
      leftCamera.aspect = width / height
      leftCamera.updateProjectionMatrix()
      leftRenderer.setSize(width, height)
    }

    if (rightCanvasRef.value && rightCamera && rightRenderer) {
      const width = rightCanvasRef.value.clientWidth
      const height = rightCanvasRef.value.clientHeight || 400
      rightCamera.aspect = width / height
      rightCamera.updateProjectionMatrix()
      rightRenderer.setSize(width, height)
    }
  })
}

// ==================== Lifecycle ====================

onMounted(async () => {
  console.log('[SplitModelViewer] onMounted called')
  console.log('[SplitModelViewer] leftUrl:', props.leftUrl, 'rightUrl:', props.rightUrl)
  console.log('[SplitModelViewer] leftCanvasRef:', leftCanvasRef.value, 'rightCanvasRef:', rightCanvasRef.value)

  if (leftCanvasRef.value) {
    console.log('[SplitModelViewer] Initializing left scene')
    const left = initScene(leftCanvasRef.value, 'left')
    leftRenderer = left.renderer
    leftScene = left.scene
    leftCamera = left.camera
    leftControls = left.controls
    startLeftAnimation()

    if (props.leftUrl) {
      console.log('[SplitModelViewer] Loading left model in onMounted:', props.leftUrl)
      try {
        await loadModel(
          props.leftUrl,
          leftScene,
          leftCamera,
          leftControls,
          (v) => { leftLoading.value = v }
        )
        emit('left-loaded')
      } catch (error) {
        emit('left-error', error as Error)
      }
    } else {
      console.warn('[SplitModelViewer] leftUrl is empty in onMounted')
    }
  } else {
    console.error('[SplitModelViewer] leftCanvasRef.value is null in onMounted!')
  }

  // Check and load pending left URL after scene init
  if (pendingLeftUrl && leftScene && leftCamera && leftControls) {
    console.log('[SplitModelViewer] Loading pending left URL:', pendingLeftUrl)
    try {
      await loadModel(
        pendingLeftUrl,
        leftScene,
        leftCamera,
        leftControls,
        (v) => { leftLoading.value = v }
      )
      emit('left-loaded')
      pendingLeftUrl = null
    } catch (error) {
      emit('left-error', error as Error)
    }
  }

  if (rightCanvasRef.value) {
    const right = initScene(rightCanvasRef.value, 'right')
    rightRenderer = right.renderer
    rightScene = right.scene
    rightCamera = right.camera
    rightControls = right.controls
    startRightAnimation()

    if (props.rightUrl) {
      try {
        await loadModel(
          props.rightUrl,
          rightScene,
          rightCamera,
          rightControls,
          (v) => { rightLoading.value = v }
        )
        emit('right-loaded')
      } catch (error) {
        emit('right-error', error as Error)
      }
    }
  }

  // Check and load pending right URL after scene init
  if (pendingRightUrl && rightScene && rightCamera && rightControls) {
    console.log('[SplitModelViewer] Loading pending right URL:', pendingRightUrl)
    try {
      await loadModel(
        pendingRightUrl,
        rightScene,
        rightCamera,
        rightControls,
        (v) => { rightLoading.value = v }
      )
      emit('right-loaded')
      pendingRightUrl = null
    } catch (error) {
      emit('right-error', error as Error)
    }
  }

  // Sync initial camera if both loaded
  if (props.syncCamera && leftControls && rightControls) {
    syncCameraToOther('left')
  }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopLeftAnimation()
  stopRightAnimation()

  if (leftRenderer) {
    leftRenderer.dispose()
  }
  if (rightRenderer) {
    rightRenderer.dispose()
  }

  window.removeEventListener('resize', handleResize)
})

// Watch for URL changes
watch(
  () => props.leftUrl,
  async (newUrl) => {
    console.log('[SplitModelViewer] leftUrl changed to:', newUrl)
    console.log('[SplitModelViewer] leftScene:', !!leftScene, 'leftCamera:', !!leftCamera, 'leftControls:', !!leftControls)

    if (newUrl) {
      if (leftScene && leftCamera && leftControls) {
        // Scene is ready, load immediately
        try {
          await loadModel(
            newUrl,
            leftScene,
            leftCamera,
            leftControls,
            (v) => { leftLoading.value = v }
          )
          emit('left-loaded')
          if (props.syncCamera) {
            syncCameraToOther('left')
          }
        } catch (error) {
          emit('left-error', error as Error)
        }
      } else {
        // Scene not ready yet, store as pending
        console.log('[SplitModelViewer] Scene not ready, storing left URL as pending:', newUrl)
        pendingLeftUrl = newUrl
      }
    }
  }
)

watch(
  () => props.rightUrl,
  async (newUrl) => {
    console.log('[SplitModelViewer] rightUrl changed to:', newUrl)

    if (newUrl) {
      if (rightScene && rightCamera && rightControls) {
        // Scene is ready, load immediately
        try {
          await loadModel(
            newUrl,
            rightScene,
            rightCamera,
            rightControls,
            (v) => { rightLoading.value = v }
          )
          emit('right-loaded')
          if (props.syncCamera) {
            syncCameraToOther('right')
          }
        } catch (error) {
          emit('right-error', error as Error)
        }
      } else {
        // Scene not ready yet, store as pending
        console.log('[SplitModelViewer] Scene not ready, storing right URL as pending:', newUrl)
        pendingRightUrl = newUrl
      }
    }
  }
)
</script>

<style scoped>
.split-model-viewer {
  display: flex;
  width: 100%;
  height: 500px;
  min-height: 400px;
  position: relative;
  background: #0f0f14;
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
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.canvas-container {
  flex: 1;
  width: 100%;
  height: 100%;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 15, 20, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #909399;
  z-index: 20;
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
  background: rgba(64, 158, 255, 0.8);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  z-index: 40;
}
</style>
