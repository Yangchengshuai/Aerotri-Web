import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { CameraInfo, Point3D } from '@/types'

export function useThreeViewer(containerRef: { value: HTMLElement | null }) {
  const isReady = ref(false)
  const showCameras = ref(true)
  const showPoints = ref(true)
  
  let scene: THREE.Scene
  let camera: THREE.PerspectiveCamera
  let renderer: THREE.WebGLRenderer
  let controls: OrbitControls
  let camerasGroup: THREE.Group
  let pointsGroup: THREE.Group
  let animationId: number

  function init() {
    if (!containerRef.value) return

    const container = containerRef.value
    const width = container.clientWidth
    const height = container.clientHeight

    // Scene
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a2e)

    // Camera
    camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000)
    camera.position.set(0, 0, 50)

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(renderer.domElement)

    // Controls
    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05

    // Groups
    camerasGroup = new THREE.Group()
    pointsGroup = new THREE.Group()
    scene.add(camerasGroup)
    scene.add(pointsGroup)

    // Axes helper
    const axesHelper = new THREE.AxesHelper(10)
    scene.add(axesHelper)

    // Start animation
    animate()

    // Handle resize
    window.addEventListener('resize', onWindowResize)

    isReady.value = true
  }

  function animate() {
    animationId = requestAnimationFrame(animate)
    controls.update()
    renderer.render(scene, camera)
  }

  function onWindowResize() {
    if (!containerRef.value) return

    const width = containerRef.value.clientWidth
    const height = containerRef.value.clientHeight

    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }

  function loadCameras(cameras: CameraInfo[]) {
    // Clear existing
    camerasGroup.clear()

    cameras.forEach((cam) => {
      // Create camera frustum
      const frustum = createCameraFrustum()
      
      // Apply rotation from quaternion
      const quaternion = new THREE.Quaternion(cam.qx, cam.qy, cam.qz, cam.qw)
      frustum.quaternion.copy(quaternion)
      
      // Apply translation (camera position is -R^T * t)
      const rotation = new THREE.Matrix4().makeRotationFromQuaternion(quaternion)
      const position = new THREE.Vector3(-cam.tx, -cam.ty, -cam.tz)
      position.applyMatrix4(rotation.transpose())
      frustum.position.copy(position)

      // Store camera info for raycasting
      frustum.userData = { camera: cam }

      camerasGroup.add(frustum)
    })

    // Auto-fit view
    fitToView()
  }

  function loadPoints(points: Point3D[]) {
    // Clear existing
    pointsGroup.clear()

    if (points.length === 0) return

    // Create geometry
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

    // Create material
    const material = new THREE.PointsMaterial({
      size: 0.1,
      vertexColors: true,
    })

    // Create points mesh
    const pointsMesh = new THREE.Points(geometry, material)
    pointsGroup.add(pointsMesh)
  }

  function createCameraFrustum(): THREE.Object3D {
    const group = new THREE.Group()
    
    // Frustum size
    const size = 1
    const depth = 2
    
    // Create wireframe pyramid
    const points = [
      new THREE.Vector3(0, 0, 0), // apex
      new THREE.Vector3(-size, -size, depth),
      new THREE.Vector3(size, -size, depth),
      new THREE.Vector3(size, size, depth),
      new THREE.Vector3(-size, size, depth),
    ]
    
    const geometry = new THREE.BufferGeometry()
    const positions = [
      // Lines from apex to corners
      ...points[0].toArray(), ...points[1].toArray(),
      ...points[0].toArray(), ...points[2].toArray(),
      ...points[0].toArray(), ...points[3].toArray(),
      ...points[0].toArray(), ...points[4].toArray(),
      // Bottom rectangle
      ...points[1].toArray(), ...points[2].toArray(),
      ...points[2].toArray(), ...points[3].toArray(),
      ...points[3].toArray(), ...points[4].toArray(),
      ...points[4].toArray(), ...points[1].toArray(),
    ]
    
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    
    const material = new THREE.LineBasicMaterial({ color: 0x00ff00 })
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
    
    camera.position.copy(center)
    camera.position.z += maxDim * 2
    
    controls.target.copy(center)
    controls.update()
  }

  function dispose() {
    if (animationId) {
      cancelAnimationFrame(animationId)
    }
    
    window.removeEventListener('resize', onWindowResize)
    
    if (renderer && containerRef.value) {
      containerRef.value.removeChild(renderer.domElement)
      renderer.dispose()
    }
  }

  // Watch visibility toggles
  watch(showCameras, (visible) => {
    camerasGroup.visible = visible
  })
  
  watch(showPoints, (visible) => {
    pointsGroup.visible = visible
  })

  onMounted(() => {
    init()
  })

  onUnmounted(() => {
    dispose()
  })

  return {
    isReady,
    showCameras,
    showPoints,
    loadCameras,
    loadPoints,
    fitToView,
  }
}
