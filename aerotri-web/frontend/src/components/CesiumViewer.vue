<template>
  <div class="cesium-viewer-root">
    <div v-if="loading" class="loading-overlay">
      <el-text>正在加载 CesiumJS...</el-text>
    </div>
    <div v-if="error" class="error-overlay">
      <el-alert
        :title="error"
        type="error"
        :closable="false"
      />
      <el-button
        type="primary"
        @click="retry"
        style="margin-top: 12px"
      >
        重试
      </el-button>
    </div>
    <div ref="container" class="cesium-container"></div>
    <div v-if="viewer" class="cesium-controls">
      <el-button
        size="small"
        @click="zoomToModel"
        style="margin-bottom: 8px"
      >
        定位到模型
      </el-button>
      <el-button
        size="small"
        @click="resetView"
        style="margin-bottom: 8px"
      >
        重置视角
      </el-button>
      <el-button
        size="small"
        @click="showModelInfo"
      >
        模型信息
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'

const props = defineProps<{
  tilesetUrl: string
}>()

const container = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let viewer: Cesium.Viewer | null = null
let currentTileset: Cesium.Cesium3DTileset | null = null

// Set Cesium base URL (required for Workers, Assets, etc.)
// This is defined in vite.config.mjs via define
;(window as any).CESIUM_BASE_URL = '/cesium/'

async function initViewer() {
  if (!container.value) return

  try {
    // Create terrain provider (async in newer Cesium versions)
    let terrainProvider: Cesium.TerrainProvider | undefined
    try {
      terrainProvider = await Cesium.createWorldTerrainAsync()
    } catch (terrainErr: any) {
      // Fallback to ellipsoid terrain if world terrain fails
      console.warn('Failed to create world terrain, using ellipsoid terrain:', terrainErr)
      terrainProvider = new Cesium.EllipsoidTerrainProvider()
    }

    // Create viewer
    viewer = new Cesium.Viewer(container.value, {
      terrainProvider: terrainProvider,
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

    // Solution 1: Disable globe and imagery for model-only viewing (Recommended)
    // This is the best solution when you only want to view the model without geographic reference
    viewer.scene.globe.show = false
    viewer.imageryLayers.removeAll()
    viewer.scene.backgroundColor = Cesium.Color.BLACK.clone()
    
    // Also disable sky box for cleaner view
    if (viewer.scene.skyBox) {
      viewer.scene.skyBox.show = false
    }
    if (viewer.scene.sun) {
      viewer.scene.sun.show = false
    }
    if (viewer.scene.moon) {
      viewer.scene.moon.show = false
    }
    if (viewer.scene.skyAtmosphere) {
      viewer.scene.skyAtmosphere.show = false
    }

    // Enable free camera rotation for local coordinate models
    // Remove axis constraints to allow unlimited rotation
    viewer.camera.constrainedAxis = undefined
    
    // Disable collision detection to allow free movement
    viewer.camera.enableCollisionDetection = false
    
    // Enable all camera controls
    const screenSpaceController = viewer.scene.screenSpaceCameraController
    screenSpaceController.enableRotate = true
    screenSpaceController.enableTranslate = true
    screenSpaceController.enableZoom = true
    screenSpaceController.enableTilt = true
    screenSpaceController.enableLook = true
    
    // Remove pitch rotation constraints to allow unlimited up/down rotation
    // This is the key fix for allowing free rotation
    const controllerAny = screenSpaceController as any
    if (controllerAny) {
      // Set pitch limits to allow full 360-degree rotation
      // Default is usually limited to prevent flipping
      controllerAny._maximumPitch = Cesium.Math.PI  // 180 degrees (straight up)
      controllerAny._minimumPitch = -Cesium.Math.PI  // -180 degrees (straight down)
      
      // Also try to remove constraints from the camera itself
      const cameraAny = viewer.camera as any
      if (cameraAny._controller) {
        const camController = cameraAny._controller as any
        if (camController) {
          camController._maximumPitch = Cesium.Math.PI
          camController._minimumPitch = -Cesium.Math.PI
        }
      }
    }
    
    console.log('✓ Camera rotation constraints removed for free rotation')

    // Load tileset
    loadTileset()

    loading.value = false
  } catch (err: any) {
    error.value = `初始化 CesiumJS 失败: ${err.message}`
    loading.value = false
  }
}

async function loadTileset() {
  if (!viewer || !props.tilesetUrl) return

  try {
    let tileset: Cesium.Cesium3DTileset

    // Try using fromUrl method (recommended in CesiumJS 1.104+)
    // If not available, fall back to constructor
    if (typeof Cesium.Cesium3DTileset.fromUrl === 'function') {
      try {
        tileset = await Cesium.Cesium3DTileset.fromUrl(props.tilesetUrl)
      } catch (fromUrlErr: any) {
        // Fallback to constructor if fromUrl fails
        console.warn('fromUrl failed, using constructor:', fromUrlErr)
        tileset = new Cesium.Cesium3DTileset({
          url: props.tilesetUrl,
        } as any)
      }
    } else {
      // Use constructor for older versions
      tileset = new Cesium.Cesium3DTileset({
        url: props.tilesetUrl,
      } as any)
    }

    if (!tileset) {
      error.value = '加载 3D Tiles 失败: 无法创建 tileset'
      console.error('Failed to create tileset')
      return
    }

    // Add tileset to scene
    viewer.scene.primitives.add(tileset)
    console.log('✓ Tileset added to scene primitives')
    
    // Store reference to tileset
    currentTileset = tileset
    
    // Force update to trigger tile loading
    viewer.scene.requestRender()

    // Add event listeners for debugging
    const tilesetAny = tileset as any
    
    // Listen for tile load events
    tileset.tileLoad.addEventListener((tile: any) => {
      console.log('✓ Tile loaded:', {
        content: tile.content,
        boundingVolume: tile.boundingVolume,
        uri: tile.content?.uri,
        url: tile.content?.uri || tile.content?._url
      })
    })
    
    // Listen for tile failed events
    tileset.tileFailed.addEventListener((tile: any, err: any) => {
      const errorMsg = err?.message || err?.toString() || String(err) || '未知错误'
      console.error('✗ Tile failed to load:', {
        tile,
        error: errorMsg,
        url: tile?.content?.uri || tile?.content?._url,
        errorObj: err
      })
      error.value = `模型加载失败: ${errorMsg}`
    })
    
    // Listen for all tiles loaded
    tileset.allTilesLoaded.addEventListener(() => {
      console.log('✓ All tiles loaded successfully')
    })
    
    // Listen for initial tiles loaded
    tileset.initialTilesLoaded.addEventListener(() => {
      console.log('✓ Initial tiles loaded')
    })
    
    // Monitor tileset ready state
    const checkReady = () => {
      const ready = tilesetAny.ready
      console.log('Tileset ready state:', ready, 'at', new Date().toISOString())
      if (ready) {
        console.log('Tileset is ready!', {
          root: tilesetAny.root,
          boundingSphere: tilesetAny.boundingSphere,
          statistics: tilesetAny.statistics
        })
      }
    }
    
    // Check ready state periodically
    let readyCheckCount = 0
    const maxReadyChecks = 100 // 10 seconds
    const readyCheckInterval = setInterval(() => {
      checkReady()
      readyCheckCount++
      if (readyCheckCount >= maxReadyChecks || tilesetAny.ready) {
        clearInterval(readyCheckInterval)
      }
    }, 100)
    
    // Log tileset URL for debugging
    console.log('Tileset URL:', props.tilesetUrl)
    console.log('Tileset object:', tileset)

    // Handle tileset ready state and zoom to it
    // Use boundingSphere as the reliable indicator of model availability
    const zoomToTileset = () => {
      if (!viewer || !tileset) return
      
      // Debug: Check tileset properties
      console.log('Tileset debug info:', {
        url: tilesetAny.url,
        root: tilesetAny.root,
        boundingSphere: tilesetAny.boundingSphere,
        ready: tilesetAny.ready,
        readyPromise: tilesetAny.readyPromise
      })
      
      const tryZoom = () => {
        const boundingSphere = tilesetAny.boundingSphere
        
        if (boundingSphere && boundingSphere.center && boundingSphere.radius) {
          const center = boundingSphere.center
          const radius = boundingSphere.radius

          const centerMagnitude = Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z)
          console.log('Tileset bounding sphere:', {
            center: { x: center.x, y: center.y, z: center.z },
            radius,
            centerMagnitude
          })

          // Check if model is in local coordinates (center near origin)
          // If center magnitude < 1000, treat as local coordinates
          const isLocalCoordinates = centerMagnitude < 1000
          
          if (isLocalCoordinates) {
            // For local coordinates, use camera.lookAt directly
            // This avoids Cesium's coordinate transformation
            const rangeMultiplier = radius < 10 ? 10 : 2.5
            const viewRange = Math.max(radius * rangeMultiplier, 10)
            
            console.log('Model in local coordinates, using camera.lookAt with range:', viewRange)
            
            try {
              // Calculate camera position: offset from center by viewRange
              // Use negative Z to fix axis orientation
              const cameraOffset = new Cesium.Cartesian3(0, 0, -viewRange)
              const cameraPosition = Cesium.Cartesian3.add(center, cameraOffset, new Cesium.Cartesian3())
              
              viewer!.camera.lookAt(
                center,
                new Cesium.HeadingPitchRange(0, 0.5, viewRange)  // Changed pitch from -0.5 to 0.5 to fix Z-axis
              )
              
              console.log('✓ Successfully positioned camera for local coordinates model')
              
              // Log current camera position for debugging
              const cameraPos = viewer!.camera.position
              console.log('Camera position after zoom:', {
                x: cameraPos.x,
                y: cameraPos.y,
                z: cameraPos.z,
                magnitude: Math.sqrt(cameraPos.x * cameraPos.x + cameraPos.y * cameraPos.y + cameraPos.z * cameraPos.z)
              })
              
              return true
            } catch (lookAtErr: any) {
              console.warn('camera.lookAt failed, trying setView:', lookAtErr)
              // Fallback: use setView with Cartesian3
              try {
                const viewRange = Math.max(radius * (radius < 10 ? 10 : 2.5), 10)
                const cameraPos = Cesium.Cartesian3.add(
                  center,
                  new Cesium.Cartesian3(0, 0, -viewRange),  // Use negative Z to fix axis orientation
                  new Cesium.Cartesian3()
                )
                viewer!.camera.setView({
                  destination: cameraPos,
                  orientation: {
                    heading: 0,
                    pitch: 0.5,  // Changed pitch from -0.5 to 0.5 to fix Z-axis
                    roll: 0
                  }
                })
                console.log('✓ Successfully positioned camera (via setView)')
                return true
              } catch (setViewErr: any) {
                console.error('setView also failed:', setViewErr)
                return false
              }
            }
          } else {
            // For geographic coordinates, use standard methods
            const rangeMultiplier = radius < 10 ? 10 : 2.5
            const viewRange = Math.max(radius * rangeMultiplier, 10)
            
            console.log('Model in geographic coordinates, using viewBoundingSphere with range:', viewRange)
            
            try {
              viewer!.camera.viewBoundingSphere(
                boundingSphere,
                new Cesium.HeadingPitchRange(0, -0.5, viewRange)
              )
              console.log('✓ Successfully zoomed to tileset')
              
              // Log current camera position for debugging
              const cameraPos = viewer!.camera.position
              console.log('Camera position after zoom:', {
                x: cameraPos.x,
                y: cameraPos.y,
                z: cameraPos.z,
                magnitude: Math.sqrt(cameraPos.x * cameraPos.x + cameraPos.y * cameraPos.y + cameraPos.z * cameraPos.z)
              })
              
              return true
            } catch (viewErr: any) {
              console.warn('viewBoundingSphere failed, trying zoomTo:', viewErr)
              // Fallback: try zoomTo
              const viewRange = Math.max(radius * (radius < 10 ? 10 : 2.5), 10)
              try {
                viewer!.zoomTo(tileset, new Cesium.HeadingPitchRange(0, -0.5, viewRange))
                console.log('✓ Successfully zoomed to tileset (via zoomTo)')
                return true
              } catch (zoomErr: any) {
                console.error('zoomTo also failed:', zoomErr)
                return false
              }
            }
          }
        } else {
          console.warn('Bounding sphere not available yet:', {
            hasBoundingSphere: !!boundingSphere,
            hasCenter: boundingSphere ? !!boundingSphere.center : false,
            hasRadius: boundingSphere ? !!boundingSphere.radius : false
          })
        }
        return false
      }

      // Try immediately
      if (tryZoom()) {
        return
      }

      // Wait a bit and retry
      setTimeout(() => {
        if (!viewer || !tileset) return
        if (tryZoom()) {
          return
        }
        
        // If still not available, try polling
        let pollCount = 0
        const maxPolls = 50 // 5 seconds
        
        const checkAndZoom = () => {
          if (tryZoom()) {
            return
          }
          
          if (pollCount < maxPolls) {
            pollCount++
            setTimeout(checkAndZoom, 100)
          } else {
            console.warn('Tileset bounding sphere not available after timeout, trying fallback')
            // Fallback: try zoomTo without bounding sphere
            try {
              viewer!.zoomTo(tileset)
            } catch (err: any) {
              console.error('Fallback zoomTo failed:', err)
            }
          }
        }
        
        checkAndZoom()
      }, 500) // Initial delay
    }

    // Try to use readyPromise if available
    if (tilesetAny.readyPromise) {
      tilesetAny.readyPromise
        .then(() => {
          console.log('Tileset loaded successfully (via readyPromise)')
          zoomToTileset()
        })
        .catch((err: any) => {
          error.value = `加载 3D Tiles 失败: ${err.message || err}`
          console.error('Error loading tileset:', err)
        })
    } else {
      // No readyPromise, use polling approach
      console.log('No readyPromise available, using polling approach')
      zoomToTileset()
    }
  } catch (err: any) {
    error.value = `加载 3D Tiles 失败: ${err.message || err}`
    console.error('Error loading tileset:', err)
  }
}

function zoomToModel() {
  if (!viewer || !currentTileset) {
    ElMessage.warning('模型尚未加载')
    return
  }

  try {
    const tilesetAny = currentTileset as any
    
    // Try to get bounding sphere - this is the most reliable way to check if model is loaded
    const tryZoom = () => {
      const boundingSphere = tilesetAny.boundingSphere
      
      if (boundingSphere && boundingSphere.center && boundingSphere.radius) {
        const center = boundingSphere.center
        const radius = boundingSphere.radius

        console.log('Model position:', {
          center: { x: center.x, y: center.y, z: center.z },
          radius
        })

        // Since we disabled globe, we can directly view the model
        // Check if model is in local coordinates
        const centerMagnitude = Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z)
        const isLocalCoordinates = centerMagnitude < 1000
        
        if (isLocalCoordinates) {
          // For local coordinates, use camera.lookAt
          const viewRange = Math.max(radius * (radius < 10 ? 10 : 2.5), 10)
          try {
            viewer!.camera.lookAt(
              center,
              new Cesium.HeadingPitchRange(0, 0.5, viewRange)  // Changed pitch from -0.5 to 0.5 to fix Z-axis
            )
            ElMessage.success('已定位到模型')
            return true
          } catch (lookAtErr: any) {
            console.warn('camera.lookAt failed, trying setView:', lookAtErr)
            // Fallback: use setView
            try {
              const cameraPos = Cesium.Cartesian3.add(
                center,
                new Cesium.Cartesian3(0, 0, -viewRange),  // Use negative Z to fix axis orientation
                new Cesium.Cartesian3()
              )
              viewer!.camera.setView({
                destination: cameraPos,
                orientation: {
                  heading: 0,
                  pitch: 0.5,  // Changed pitch from -0.5 to 0.5 to fix Z-axis
                  roll: 0
                }
              })
              ElMessage.success('已定位到模型')
              return true
            } catch (setViewErr: any) {
              console.error('setView also failed:', setViewErr)
              return false
            }
          }
        } else {
          // For geographic coordinates, use standard methods
          try {
            viewer!.camera.viewBoundingSphere(
              boundingSphere,
              new Cesium.HeadingPitchRange(
                0,        // heading: 0 degrees (north)
                -0.5,     // pitch: -0.5 radians (look down slightly)
                Math.max(radius * 2.5, 10)  // range: 2.5x the radius, minimum 10 units
              )
            )
            ElMessage.success('已定位到模型')
            return true
          } catch (viewErr: any) {
            console.warn('viewBoundingSphere failed, trying zoomTo:', viewErr)
            // Fallback to zoomTo
            try {
              viewer!.zoomTo(currentTileset!, new Cesium.HeadingPitchRange(0, -0.5, Math.max(radius * 2.5, 10)))
              ElMessage.success('已定位到模型')
              return true
            } catch (zoomErr: any) {
              console.error('zoomTo also failed:', zoomErr)
              return false
            }
          }
        }
      } else {
        return false
      }
    }

    // Try immediately
    if (tryZoom()) {
      return
    }

    // If bounding sphere not available, wait a bit and retry
    ElMessage.info('模型正在加载，请稍候...')
    let pollCount = 0
    const maxPolls = 50 // 5 seconds (50 * 100ms)
    
    const checkAndZoom = () => {
      if (tryZoom()) {
        return // Success
      }
      
      if (pollCount < maxPolls) {
        pollCount++
        setTimeout(checkAndZoom, 100)
      } else {
        // Timeout - try fallback methods
        ElMessage.warning('模型加载超时，尝试使用备用方法定位...')
        
        // Fallback 1: Try zoomTo without bounding sphere
        try {
          viewer!.zoomTo(currentTileset!)
          ElMessage.success('已定位到模型（使用备用方法）')
        } catch (err1: any) {
          console.warn('Fallback zoomTo failed:', err1)
          
          // Fallback 2: Set camera to origin with reasonable distance
          try {
            // For local coordinates, use Cartesian3 directly
            const tilesetAny = currentTileset as any
            const boundingSphere = tilesetAny?.boundingSphere
            if (boundingSphere && boundingSphere.center) {
              const center = boundingSphere.center
              const centerMagnitude = Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z)
              if (centerMagnitude < 1000) {
                // Local coordinates: use Cartesian3
                const cameraPos = Cesium.Cartesian3.add(
                  center,
                  new Cesium.Cartesian3(0, 0, -100),
                  new Cesium.Cartesian3()
                )
                viewer!.camera.setView({
                  destination: cameraPos,
                  orientation: {
                    heading: 0,
                    pitch: 0.5,  // Fixed Z-axis orientation
                    roll: 0
                  }
                })
              } else {
                // Geographic coordinates: use fromDegrees
                viewer!.camera.setView({
                  destination: Cesium.Cartesian3.fromDegrees(0, 0, 1000),
                  orientation: {
                    heading: 0,
                    pitch: -0.5,
                    roll: 0
                  }
                })
              }
            } else {
              viewer!.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(0, 0, 1000),
                orientation: {
                  heading: 0,
                  pitch: -0.5,
                  roll: 0
                }
              })
            }
            ElMessage.info('已重置相机位置，请手动查找模型')
          } catch (err2: any) {
            console.error('All fallback methods failed:', err2)
            ElMessage.error('定位失败，请检查模型是否已加载')
          }
        }
      }
    }
    
    checkAndZoom()
  } catch (err: any) {
    console.error('Failed to zoom to model:', err)
    ElMessage.error(`定位到模型失败: ${err.message || err}`)
  }
}

function showModelInfo() {
  if (!viewer || !currentTileset) {
    ElMessage.warning('模型尚未加载')
    return
  }

  const tilesetAny = currentTileset as any
  const boundingSphere = tilesetAny.boundingSphere
  const statistics = tilesetAny.statistics
  const root = tilesetAny.root
  
  const info: string[] = []
  info.push('=== 模型信息 ===')
  info.push(`URL: ${tilesetAny.url || 'N/A'}`)
  info.push(`Ready: ${tilesetAny.ready || false}`)
  
  if (root) {
    const rootContent = root.content
    const rootUri = rootContent?._url || rootContent?.uri || rootContent?._resource?.url || 'N/A'
    info.push(`Root Content URI: ${rootUri}`)
    info.push(`Root Content State: ${rootContent?._state || rootContent?.state || 'N/A'}`)
    info.push(`Root Content Ready: ${rootContent?._ready || rootContent?.ready || false}`)
    
    // Check if root tile has children
    if (root.children && root.children.length > 0) {
      info.push(`Root Children Count: ${root.children.length}`)
    }
  }
  
  if (boundingSphere) {
    const center = boundingSphere.center
    const radius = boundingSphere.radius
    info.push(`中心点: (${center.x.toFixed(3)}, ${center.y.toFixed(3)}, ${center.z.toFixed(3)})`)
    info.push(`半径: ${radius.toFixed(3)}`)
    info.push(`中心距离原点: ${Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z).toFixed(3)}`)
  } else {
    info.push('边界球: 不可用')
  }
  
  if (statistics) {
    info.push(`几何体数: ${statistics.geometriesLength || 'N/A'}`)
    info.push(`纹理数: ${statistics.texturesByteLength || 'N/A'}`)
    info.push(`已加载 Tile 数: ${statistics.numberOfTilesLoaded || 'N/A'}`)
    info.push(`可见 Tile 数: ${statistics.numberOfTilesVisible || 'N/A'}`)
  }
  
  const cameraPos = viewer.camera.position
  info.push(`\n相机位置: (${cameraPos.x.toFixed(2)}, ${cameraPos.y.toFixed(2)}, ${cameraPos.z.toFixed(2)})`)
  info.push(`相机距离原点: ${Math.sqrt(cameraPos.x * cameraPos.x + cameraPos.y * cameraPos.y + cameraPos.z * cameraPos.z).toFixed(2)}`)
  
  console.log(info.join('\n'))
  ElMessage.info('模型信息已输出到控制台，请按 F12 查看')
}

function resetView() {
  if (!viewer) return

  // Reset to model view if available, otherwise default view
  const tilesetAny = currentTileset as any
  if (currentTileset && tilesetAny) {
    const boundingSphere = tilesetAny.boundingSphere
    if (boundingSphere && boundingSphere.center) {
      const center = boundingSphere.center
      const centerMagnitude = Math.sqrt(center.x * center.x + center.y * center.y + center.z * center.z)
      
      if (centerMagnitude < 1000) {
        // Local coordinates: reset using lookAt with fixed Z-axis
        const radius = boundingSphere.radius || 10
        const viewRange = Math.max(radius * 10, 100)
        try {
          viewer.camera.lookAt(
            center,
            new Cesium.HeadingPitchRange(0, 0.5, viewRange)  // Fixed Z-axis orientation
          )
          return
        } catch (err: any) {
          console.warn('lookAt failed in resetView, using setView:', err)
        }
      }
    }
    
    // Try zoomToModel as fallback
    zoomToModel()
  } else {
    // Default view: origin with reasonable distance
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(0, 0, 1000),
      orientation: {
        heading: 0,
        pitch: -0.5,
        roll: 0
      }
    })
  }
}

function retry() {
  error.value = null
  loading.value = true
  init()
}

async function init() {
  try {
    await initViewer()
  } catch (err: any) {
    error.value = `初始化 CesiumJS 失败: ${err.message}`
    loading.value = false
  }
}

onMounted(() => {
  init()
})

onUnmounted(() => {
  if (viewer) {
    viewer.destroy()
    viewer = null
  }
})

watch(() => props.tilesetUrl, () => {
  if (viewer && props.tilesetUrl) {
    // Remove existing tileset
    viewer.scene.primitives.removeAll()
    currentTileset = null
    // Load new tileset
    loadTileset()
  }
}, { immediate: false })
</script>

<style scoped>
.cesium-viewer-root {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.cesium-container {
  width: 100%;
  height: 100%;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  background: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.cesium-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
}
</style>

