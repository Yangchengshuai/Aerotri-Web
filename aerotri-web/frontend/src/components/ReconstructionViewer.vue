<template>
  <div class="viewer-root">
    <div class="meta">
      <el-text type="info">
        文件类型：{{ fileTypeLabel }}
      </el-text>
    </div>
    <div ref="container" class="canvas-container"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader'

const props = defineProps<{
  fileUrl: string
  fileType: 'point_cloud' | 'mesh' | 'texture' | 'other'
}>()

const container = ref<HTMLDivElement | null>(null)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let animationId: number | null = null

const fileTypeLabel = computed(() => {
  switch (props.fileType) {
    case 'point_cloud':
      return '点云'
    case 'mesh':
      return '网格'
    case 'texture':
      return '纹理模型'
    default:
      return '其他'
  }
})

function initScene() {
  if (!container.value) return

  const width = container.value.clientWidth
  const height = container.value.clientHeight || 400

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x020617)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
  camera.position.set(0, 0, 5)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.value.innerHTML = ''
  container.value.appendChild(renderer.domElement)

  const light = new THREE.DirectionalLight(0xffffff, 1)
  light.position.set(1, 1, 1)
  scene.add(light)
  scene.add(new THREE.AmbientLight(0xffffff, 0.3))

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
}

function fitToObject(object: THREE.Object3D) {
  if (!camera || !controls) return

  const box = new THREE.Box3().setFromObject(object)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())

  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = (camera.fov * Math.PI) / 180
  let cameraZ = Math.abs((maxDim / 2) / Math.tan(fov / 2))
  cameraZ *= 1.5

  camera.position.set(center.x, center.y, center.z + cameraZ)
  camera.lookAt(center)
  controls.target.copy(center)
  controls.update()
}

function loadModel() {
  if (!scene) return

  // Remove previous content except lights
  const toRemove = scene.children.filter(
    (c) => !(c instanceof THREE.Light),
  )
  toRemove.forEach((c) => scene!.remove(c))

  if (props.fileUrl.endsWith('.ply')) {
    const loader = new PLYLoader()
    loader.load(
      props.fileUrl,
      (geometry) => {
        geometry.computeVertexNormals()
        let object: THREE.Object3D
        if (props.fileType === 'point_cloud') {
          const material = new THREE.PointsMaterial({
            size: 0.01,
            vertexColors: !!geometry.getAttribute('color'),
          })
          object = new THREE.Points(geometry, material)
        } else {
          const material = new THREE.MeshStandardMaterial({
            color: 0xeeeeee,
            flatShading: false,
            metalness: 0.1,
            roughness: 0.9,
            vertexColors: !!geometry.getAttribute('color'),
          })
          object = new THREE.Mesh(geometry, material)
        }
        scene!.add(object)
        fitToObject(object)
      },
    )
  } else if (props.fileUrl.endsWith('.obj')) {
    const loader = new OBJLoader()
    loader.load(props.fileUrl, (object) => {
      scene!.add(object)
      fitToObject(object)
    })
  }
}

function animate() {
  if (!renderer || !scene || !camera) return
  animationId = requestAnimationFrame(animate)
  if (controls) {
    controls.update()
  }
  renderer.render(scene, camera)
}

function handleResize() {
  if (!container.value || !camera || !renderer) return
  const width = container.value.clientWidth
  const height = container.value.clientHeight || 400
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

onMounted(() => {
  initScene()
  loadModel()
  animate()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (animationId !== null) {
    cancelAnimationFrame(animationId)
  }
  if (renderer) {
    renderer.dispose()
  }
})

watch(
  () => props.fileUrl,
  () => {
    loadModel()
  },
)
</script>

<style scoped>
.viewer-root {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.canvas-container {
  width: 100%;
  height: 60vh;
  min-height: 360px;
  border-radius: 8px;
  overflow: hidden;
  background: #020617;
}
</style>


