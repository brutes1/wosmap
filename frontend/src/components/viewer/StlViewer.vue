<template>
  <div class="relative w-full h-full">
    <!-- Canvas container -->
    <div ref="containerRef" class="w-full h-full" />

    <!-- Loading overlay -->
    <div
      v-if="isLoading"
      class="absolute inset-0 flex items-center justify-center bg-white/80"
    >
      <div class="flex flex-col items-center gap-3">
        <svg class="w-10 h-10 animate-spin text-primary-500" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span class="text-sm text-slate-600 font-medium">Loading 3D preview...</span>
      </div>
    </div>

    <!-- Error state -->
    <div
      v-if="error"
      class="absolute inset-0 flex items-center justify-center bg-danger-50/50"
    >
      <div class="text-center p-6">
        <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-danger-100 flex items-center justify-center">
          <svg class="w-6 h-6 text-danger-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <p class="text-danger-600 font-medium mb-1">Failed to load model</p>
        <p class="text-sm text-slate-500">{{ error }}</p>
      </div>
    </div>

    <!-- Controls hint -->
    <div
      v-if="!isLoading && !error && hasModel"
      class="absolute bottom-4 left-4 px-3 py-1.5 bg-black/50 text-white text-xs rounded-lg backdrop-blur-sm"
    >
      Drag to rotate, scroll to zoom
    </div>
  </div>
</template>

<script>
import { ref, shallowRef, watch, onMounted, onUnmounted } from 'vue'
import { useElementSize } from '@vueuse/core'
import * as THREE from 'three'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export default {
  name: 'StlViewer',

  props: {
    stlUrl: {
      type: String,
      default: null
    },
    backgroundColor: {
      type: String,
      default: '#f8fafc'
    },
    modelColor: {
      type: String,
      default: '#94a3b8'
    }
  },

  emits: ['load', 'error', 'loading'],

  setup(props, { emit, expose }) {
    // Template refs
    const containerRef = ref(null)
    const { width, height } = useElementSize(containerRef)

    // Three.js objects (shallowRef to avoid Vue reactivity overhead)
    const renderer = shallowRef(null)
    const scene = shallowRef(null)
    const camera = shallowRef(null)
    const controls = shallowRef(null)
    const currentMesh = shallowRef(null)

    // State
    const isLoading = ref(false)
    const error = ref(null)
    const hasModel = ref(false)

    // Animation frame ID
    let animationId = null

    function init() {
      if (!containerRef.value || !width.value || !height.value) return

      // Scene
      scene.value = new THREE.Scene()
      scene.value.background = new THREE.Color(props.backgroundColor)

      // Camera
      camera.value = new THREE.PerspectiveCamera(
        45,
        width.value / height.value,
        0.1,
        10000
      )
      camera.value.position.set(100, 100, 100)

      // Renderer
      renderer.value = new THREE.WebGLRenderer({
        antialias: true,
        powerPreference: 'high-performance'
      })
      renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.value.setSize(width.value, height.value)
      renderer.value.shadowMap.enabled = true
      renderer.value.shadowMap.type = THREE.PCFSoftShadowMap
      containerRef.value.appendChild(renderer.value.domElement)

      // Lighting
      setupLighting()

      // Ground plane for shadows
      const groundGeometry = new THREE.PlaneGeometry(10000, 10000)
      const groundMaterial = new THREE.ShadowMaterial({ opacity: 0.1 })
      const ground = new THREE.Mesh(groundGeometry, groundMaterial)
      ground.rotation.x = -Math.PI / 2
      ground.position.y = -1
      ground.receiveShadow = true
      scene.value.add(ground)

      // Controls
      controls.value = new OrbitControls(camera.value, renderer.value.domElement)
      controls.value.enableDamping = true
      controls.value.dampingFactor = 0.05
      controls.value.screenSpacePanning = true
      controls.value.minDistance = 10
      controls.value.maxDistance = 5000

      // Start render loop
      animate()
    }

    function setupLighting() {
      // Hemisphere light for natural outdoor terrain lighting
      const hemiLight = new THREE.HemisphereLight(0xffffff, 0x8d8d8d, 1.0)
      scene.value.add(hemiLight)

      // Main directional light (sun) for shadows and definition
      const dirLight = new THREE.DirectionalLight(0xffffff, 1.5)
      dirLight.position.set(50, 100, 50)
      dirLight.castShadow = true
      dirLight.shadow.mapSize.width = 2048
      dirLight.shadow.mapSize.height = 2048
      dirLight.shadow.camera.near = 0.5
      dirLight.shadow.camera.far = 500
      dirLight.shadow.camera.left = -200
      dirLight.shadow.camera.right = 200
      dirLight.shadow.camera.top = 200
      dirLight.shadow.camera.bottom = -200
      scene.value.add(dirLight)

      // Soft fill light from opposite side
      const fillLight = new THREE.DirectionalLight(0xffffff, 0.5)
      fillLight.position.set(-50, 50, -50)
      scene.value.add(fillLight)

      // Ambient for base illumination
      const ambient = new THREE.AmbientLight(0xffffff, 0.3)
      scene.value.add(ambient)
    }

    function animate() {
      animationId = requestAnimationFrame(animate)
      if (controls.value) controls.value.update()
      if (renderer.value && scene.value && camera.value) {
        renderer.value.render(scene.value, camera.value)
      }
    }

    async function loadSTL(url) {
      if (!url || !scene.value) return

      isLoading.value = true
      error.value = null
      emit('loading', true)

      // Dispose previous mesh
      disposeMesh()

      try {
        const loader = new STLLoader()
        const geometry = await loader.loadAsync(url)

        // Material optimized for tactile terrain
        const material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(props.modelColor),
          roughness: 0.7,
          metalness: 0.1,
          flatShading: false
        })

        currentMesh.value = new THREE.Mesh(geometry, material)
        currentMesh.value.castShadow = true
        currentMesh.value.receiveShadow = true
        scene.value.add(currentMesh.value)

        // Auto-center and fit to view
        fitCameraToObject(currentMesh.value)

        hasModel.value = true
        emit('load', { triangles: geometry.attributes.position.count / 3 })
      } catch (err) {
        error.value = err.message || 'Failed to load STL file'
        emit('error', err)
      } finally {
        isLoading.value = false
        emit('loading', false)
      }
    }

    function fitCameraToObject(object) {
      const box = new THREE.Box3().setFromObject(object)
      const boxSize = box.getSize(new THREE.Vector3()).length()
      const boxCenter = box.getCenter(new THREE.Vector3())

      // Frame the object with some padding
      const sizeToFit = boxSize * 1.2
      const halfFovY = THREE.MathUtils.degToRad(camera.value.fov * 0.5)
      const distance = sizeToFit / Math.tan(halfFovY)

      // Position camera
      const direction = new THREE.Vector3(1, 0.6, 1).normalize()
      camera.value.position.copy(
        direction.multiplyScalar(distance).add(boxCenter)
      )

      // Update near/far planes
      camera.value.near = boxSize / 100
      camera.value.far = boxSize * 100
      camera.value.updateProjectionMatrix()

      // Point camera at center
      camera.value.lookAt(boxCenter)

      // Update controls target
      if (controls.value) {
        controls.value.target.copy(boxCenter)
        controls.value.update()
      }
    }

    function handleResize() {
      if (!camera.value || !renderer.value || !width.value || !height.value) return

      camera.value.aspect = width.value / height.value
      camera.value.updateProjectionMatrix()
      renderer.value.setSize(width.value, height.value)
    }

    function disposeMesh() {
      if (currentMesh.value) {
        scene.value?.remove(currentMesh.value)
        currentMesh.value.geometry?.dispose()
        if (currentMesh.value.material) {
          if (Array.isArray(currentMesh.value.material)) {
            currentMesh.value.material.forEach(m => m.dispose())
          } else {
            currentMesh.value.material.dispose()
          }
        }
        currentMesh.value = null
        hasModel.value = false
      }
    }

    function dispose() {
      // Stop animation loop
      if (animationId) {
        cancelAnimationFrame(animationId)
        animationId = null
      }

      // Dispose mesh
      disposeMesh()

      // Dispose controls
      if (controls.value) {
        controls.value.dispose()
        controls.value = null
      }

      // Dispose renderer
      if (renderer.value) {
        renderer.value.dispose()
        renderer.value.forceContextLoss()
        if (containerRef.value && renderer.value.domElement) {
          containerRef.value.removeChild(renderer.value.domElement)
        }
        renderer.value = null
      }

      // Dispose scene objects
      if (scene.value) {
        scene.value.traverse((object) => {
          if (object.geometry) object.geometry.dispose()
          if (object.material) {
            if (Array.isArray(object.material)) {
              object.material.forEach(m => m.dispose())
            } else {
              object.material.dispose()
            }
          }
        })
        scene.value = null
      }

      camera.value = null
    }

    // Watch for URL changes
    watch(() => props.stlUrl, (newUrl) => {
      if (newUrl) loadSTL(newUrl)
    }, { immediate: false })

    // Watch for container resize
    watch([width, height], () => {
      handleResize()
    })

    // Pause animation when tab is hidden
    function handleVisibilityChange() {
      if (document.hidden) {
        if (animationId) {
          cancelAnimationFrame(animationId)
          animationId = null
        }
      } else if (renderer.value) {
        animate()
      }
    }

    onMounted(() => {
      // Wait for container to have size
      setTimeout(() => {
        init()
        if (props.stlUrl) loadSTL(props.stlUrl)
      }, 0)

      document.addEventListener('visibilitychange', handleVisibilityChange)
    })

    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      dispose()
    })

    // Expose methods
    expose({
      reload: () => loadSTL(props.stlUrl),
      fitToView: () => currentMesh.value && fitCameraToObject(currentMesh.value)
    })

    return {
      containerRef,
      isLoading,
      error,
      hasModel
    }
  }
}
</script>
