<template>
  <div class="bg-gradient-to-br from-success-500/10 to-surface-1 rounded-2xl border border-success-500/20 p-6">
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-full bg-success-500/90 flex items-center justify-center flex-shrink-0">
        <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h3 class="text-xl font-display font-bold text-white">Map Ready!</h3>
    </div>

    <!-- File info -->
    <div v-if="fileInfo" class="mb-6 p-4 bg-navy-950/50 rounded-xl">
      <p class="font-semibold text-white mb-2 break-all">{{ fileInfo.filename }}</p>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
        <div>
          <span class="text-white/50">Size:</span>
          <span class="ml-1 font-medium text-white/80">{{ fileInfo.size_human }}</span>
        </div>
        <div>
          <span class="text-white/50">Triangles:</span>
          <span class="ml-1 font-medium text-white/80">{{ formatNumber(fileInfo.triangles) }}</span>
        </div>
        <div>
          <span class="text-white/50">Dimensions:</span>
          <span class="ml-1 font-medium text-white/80">
            {{ fileInfo.dimensions?.x_mm }} x {{ fileInfo.dimensions?.y_mm }} x {{ fileInfo.dimensions?.z_mm }} mm
          </span>
        </div>
      </div>

      <!-- Terrain elevation stats -->
      <div v-if="mapType === 'terrain' && jobMetadata" class="mt-3 pt-3 border-t border-white/[0.06] grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
        <div>
          <span class="text-white/50">Min elevation:</span>
          <span class="ml-1 font-medium text-white/80">{{ jobMetadata.min_elevation_m }}m</span>
        </div>
        <div>
          <span class="text-white/50">Peak elevation:</span>
          <span class="ml-1 font-medium text-white/80">{{ jobMetadata.max_elevation_m }}m</span>
        </div>
        <div>
          <span class="text-white/50">Relief range:</span>
          <span class="ml-1 font-medium text-white/80">{{ jobMetadata.elevation_range_m }}m</span>
        </div>
      </div>
    </div>

    <!-- Primary Download - ZIP with all files -->
    <div class="flex flex-col sm:flex-row gap-3 mb-4">
      <a
        :href="downloadAllUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-primary-500 hover:bg-primary-400 text-navy-950 font-semibold rounded-xl shadow-lg shadow-primary-500/20 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download All (ZIP)
      </a>

      <!-- 3MF Download - only shown when slicer is available -->
      <a
        v-if="slicerAvailable"
        :href="threemfUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-accent-500 hover:bg-accent-600 text-white font-semibold rounded-xl shadow-lg shadow-accent-500/20 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        Download 3MF
      </a>

      <button
        @click="$emit('print')"
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-surface-2 hover:bg-surface-3 text-white font-semibold border border-white/[0.08] rounded-xl transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Send to Printer
      </button>
    </div>

    <!-- Multi-Color Section (Collapsible) — street mode only -->
    <div v-if="mapType !== 'terrain'" class="border border-white/[0.06] rounded-xl overflow-hidden">
      <button
        @click="showMultiColor = !showMultiColor"
        class="w-full flex items-center justify-between p-4 bg-surface-1 hover:bg-surface-2 transition-colors"
      >
        <div class="flex items-center gap-3">
          <div class="flex -space-x-1">
            <div class="w-4 h-4 rounded-full bg-red-500 border-2 border-surface-1"></div>
            <div class="w-4 h-4 rounded-full bg-gray-500 border-2 border-surface-1"></div>
            <div class="w-4 h-4 rounded-full bg-blue-500 border-2 border-surface-1"></div>
            <div class="w-4 h-4 rounded-full bg-green-500 border-2 border-surface-1"></div>
          </div>
          <span class="font-medium text-white/80">Multi-Color Printing (AMS)</span>
        </div>
        <svg
          class="w-5 h-5 text-white/40 transition-transform"
          :class="{ 'rotate-180': showMultiColor }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div v-if="showMultiColor" class="p-4 space-y-4">
        <p class="text-sm text-white/60">
          The ZIP includes all layers. Download individual layers here if needed.
        </p>

        <!-- Layer Downloads Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <a
            v-for="layer in layers"
            :key="layer.id"
            :href="getLayerUrl(layer.id)"
            download
            class="flex items-center gap-2 px-3 py-2 bg-navy-950/50 hover:bg-surface-2 border border-white/[0.06] rounded-lg text-sm font-medium transition-colors"
          >
            <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: layer.color }"></div>
            <span class="text-white/80">{{ layer.name }}</span>
          </a>
        </div>

        <!-- Bambu Studio instructions -->
        <div class="text-xs text-white/60 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 space-y-1">
          <p class="font-semibold text-amber-400">Bambu Studio import:</p>
          <ol class="list-decimal list-inside space-y-0.5 text-white/60">
            <li>Import first STL (Base recommended)</li>
            <li>Right-click object → <strong class="text-white/80">Add Part</strong> → select next STL</li>
            <li>Repeat for each layer (keeps alignment)</li>
            <li>Select each part → assign to filament slot</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getDownloadUrl, getDownloadAllUrl } from '../../api.js'

export default {
  name: 'GeneratorResults',

  props: {
    jobId: {
      type: String,
      required: true
    },
    fileInfo: {
      type: Object,
      default: null
    },
    jobMetadata: {
      type: Object,
      default: null
    },
    mapType: {
      type: String,
      default: 'standard'
    },
    stlUrl: {
      type: String,
      required: true
    },
    threemfUrl: {
      type: String,
      required: true
    },
    slicerAvailable: {
      type: Boolean,
      default: false
    }
  },

  emits: ['print'],

  data() {
    return {
      showMultiColor: false,
      layers: [
        { id: 'buildings', name: 'Buildings', color: '#CC4444' },
        { id: 'roads', name: 'Roads', color: '#808080' },
        { id: 'trails', name: 'Trails', color: '#8B4513' },
        { id: 'water', name: 'Water', color: '#4488CC' },
        { id: 'parks', name: 'Parks', color: '#44AA44' },
        { id: 'base', name: 'Base', color: '#FFFFFF' },
      ]
    }
  },

  computed: {
    downloadAllUrl() {
      return getDownloadAllUrl(this.jobId)
    }
  },

  methods: {
    formatNumber(num) {
      if (num === null || num === undefined) return '-'
      return num.toLocaleString()
    },

    getLayerUrl(layerId) {
      return getDownloadUrl(this.jobId, `stl_${layerId}`)
    }
  }
}
</script>
