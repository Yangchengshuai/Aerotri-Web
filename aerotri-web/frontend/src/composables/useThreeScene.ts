import { ref, onUnmounted, type Ref } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

export interface ThreeSceneSetup {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  renderer: THREE.WebGLRenderer
  controls: OrbitControls
  rootGroup: THREE.Group
  camerasGroup: THREE.Group
  pointsGroup: THREE.Group
  animationId: number | null
  resizeObserver: ResizeObserver | null
}

export function useThreeScene(
  containerRef: Ref<HTMLElement | null>,
  onInitError?: (error: string) => void
) {
  const scene = ref<THREE.Scene | null>(null)
  const camera = ref<THREE.PerspectiveCamera | null>(null)
  const renderer = ref<THREE.WebGLRenderer | null>(null)
  const controls = ref<OrbitControls | null>(null)
  const rootGroup = ref<THREE.Group | null>(null)
  const camerasGroup = ref<THREE.Group | null>(null)
  const pointsGroup = ref<THREE.Group | null>(null)
  const animationId = ref<number | null>(null)
  const resizeObserver = ref<ResizeObserver | null>(null)
  const initialized = ref(false)
  const initError = ref<string | null>(null)

  let lastContainerWidth = 0
  let lastContainerHeight = 0
  let ensureSizeRaf: number | null = null
  let ensureSizeFrames = 0

  function initThree() {
    if (!containerRef.value) return
    const container = containerRef.value
    const rect = container.getBoundingClientRect()
    const width = Math.max(1, Math.floor(rect.width))
    const height = Math.max(1, Math.floor(rect.height))

    // Scene
    const threeScene = new THREE.Scene()
    threeScene.background = new THREE.Color(0x202124) // Dark grey background
    scene.value = threeScene

    // Camera
    const threeCamera = new THREE.PerspectiveCamera(60, width / height, 0.01, 100000)
    threeCamera.position.set(10, 10, 10)
    threeCamera.up.set(0, 1, 0) // Ensure Y is up
    camera.value = threeCamera

    // Renderer (guard WebGL context creation failures)
    try {
      const threeRenderer = new THREE.WebGLRenderer({ antialias: true })
      threeRenderer.setSize(width, height)
      threeRenderer.setPixelRatio(window.devicePixelRatio)
      threeRenderer.domElement.style.display = 'block'
      threeRenderer.domElement.style.width = '100%'
      threeRenderer.domElement.style.height = '100%'
      container.appendChild(threeRenderer.domElement)
      renderer.value = threeRenderer
    } catch (err: any) {
      console.error('Failed to create WebGL renderer:', err)
      const errorMsg = '浏览器禁用或不支持 WebGL，无法渲染 3D 视图。请开启硬件加速或更换支持 WebGL 的浏览器/运行环境。'
      initError.value = errorMsg
      if (onInitError) {
        onInitError(errorMsg)
      }
      return
    }

    // Controls
    const threeControls = new OrbitControls(threeCamera, renderer.value!.domElement)
    threeControls.enableDamping = true
    threeControls.dampingFactor = 0.05
    threeControls.enablePan = true
    threeControls.enableZoom = true
    threeControls.enableRotate = true
    threeControls.screenSpacePanning = true
    controls.value = threeControls

    // Groups
    const threeRootGroup = new THREE.Group()
    // COLMAP uses Y-down, Z-forward. Three.js uses Y-up, Z-backward.
    // Rotate 180 deg around X to align them generally
    threeRootGroup.rotation.x = Math.PI
    threeScene.add(threeRootGroup)
    rootGroup.value = threeRootGroup

    const threeCamerasGroup = new THREE.Group()
    const threePointsGroup = new THREE.Group()
    threeRootGroup.add(threeCamerasGroup)
    threeRootGroup.add(threePointsGroup)
    camerasGroup.value = threeCamerasGroup
    pointsGroup.value = threePointsGroup

    // Axes helper
    const axesHelper = new THREE.AxesHelper(10)
    threeScene.add(axesHelper)

    // Grid helper
    const gridHelper = new THREE.GridHelper(100, 100, 0x444444, 0x222222)
    threeScene.add(gridHelper)

    // Start animation
    animate()

    // Handle resize
    window.addEventListener('resize', onWindowResize)

    // Observe container resize
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (lastContainerWidth === 0 && lastContainerHeight === 0 && (width > 0 || height > 0)) {
          onWindowResize()
          setTimeout(() => fitToView(), 100)
        } else if (width !== lastContainerWidth || height !== lastContainerHeight) {
          onWindowResize()
        }
        lastContainerWidth = width
        lastContainerHeight = height
      }
    })
    observer.observe(container)
    resizeObserver.value = observer

    initialized.value = true
    startEnsureCanvasSizedLoop()
  }

  function animate() {
    if (!renderer.value || !scene.value || !camera.value || !controls.value) return
    animationId.value = requestAnimationFrame(animate)
    controls.value.update()
    renderer.value.render(scene.value, camera.value)
  }

  function onWindowResize() {
    if (!containerRef.value || !camera.value || !renderer.value) return

    const rect = containerRef.value.getBoundingClientRect()
    const width = Math.max(1, Math.floor(rect.width))
    const height = Math.max(1, Math.floor(rect.height))

    camera.value.aspect = width / height
    camera.value.updateProjectionMatrix()
    renderer.value.setPixelRatio(window.devicePixelRatio)
    renderer.value.setSize(width, height)
  }

  function startEnsureCanvasSizedLoop() {
    if (ensureSizeRaf) return
    ensureSizeFrames = 0

    const tick = () => {
      ensureSizeFrames += 1
      ensureSizeRaf = requestAnimationFrame(tick)

      if (!initialized.value || !containerRef.value || !renderer.value || !camera.value) return

      const rect = containerRef.value.getBoundingClientRect()
      const w = Math.max(1, Math.floor(rect.width))
      const h = Math.max(1, Math.floor(rect.height))

      if (w <= 1 || h <= 1) return

      const size = renderer.value.getSize(new THREE.Vector2())
      const changed = Math.floor(size.x) !== w || Math.floor(size.y) !== h
      if (changed) {
        camera.value.aspect = w / h
        camera.value.updateProjectionMatrix()
        renderer.value.setPixelRatio(window.devicePixelRatio)
        renderer.value.setSize(w, h)
        setTimeout(() => fitToView(), 0)
      }

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

  function fitToView() {
    if (!camerasGroup.value || !pointsGroup.value || !camera.value || !controls.value) return

    const box = new THREE.Box3()

    if (camerasGroup.value.children.length > 0) {
      box.expandByObject(camerasGroup.value)
    }
    if (pointsGroup.value.children.length > 0) {
      box.expandByObject(pointsGroup.value)
    }

    if (box.isEmpty()) return

    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    const radius = Math.max(1e-6, maxDim * 0.5)

    camera.value.near = Math.max(0.001, radius / 1000)
    camera.value.far = Math.max(1000, radius * 500)
    camera.value.updateProjectionMatrix()

    const fov = (camera.value.fov * Math.PI) / 180
    const dist = radius / Math.sin(fov / 2)
    const dir = new THREE.Vector3(1, 1, 1).normalize()
    camera.value.position.copy(center.clone().add(dir.multiplyScalar(dist)))

    controls.value.target.copy(center)
    controls.value.update()
  }

  function dispose() {
    stopEnsureCanvasSizedLoop()
    if (animationId.value) {
      cancelAnimationFrame(animationId.value)
      animationId.value = null
    }

    window.removeEventListener('resize', onWindowResize)
    if (resizeObserver.value && containerRef.value) {
      resizeObserver.value.unobserve(containerRef.value)
      resizeObserver.value.disconnect()
      resizeObserver.value = null
    }

    if (renderer.value && containerRef.value) {
      containerRef.value.removeChild(renderer.value.domElement)
      renderer.value.dispose()
      renderer.value = null
    }

    scene.value = null
    camera.value = null
    controls.value = null
    rootGroup.value = null
    camerasGroup.value = null
    pointsGroup.value = null
    initialized.value = false
  }

  onUnmounted(() => {
    dispose()
  })

  return {
    scene,
    camera,
    renderer,
    controls,
    rootGroup,
    camerasGroup,
    pointsGroup,
    initialized,
    initError,
    initThree,
    fitToView,
    dispose,
  }
}

