<template>
  <div class="bg-gradient-to-br from-success-500/5 to-white rounded-2xl border border-success-500/20 p-6 mt-6">
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-full bg-success-500 flex items-center justify-center flex-shrink-0">
        <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h3 class="text-xl font-bold text-slate-900">Map Ready!</h3>
    </div>

    <!-- File info -->
    <div v-if="fileInfo" class="mb-6 p-4 bg-slate-50 rounded-xl">
      <p class="font-semibold text-slate-800 mb-2 break-all">{{ fileInfo.filename }}</p>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
        <div>
          <span class="text-slate-500">Size:</span>
          <span class="ml-1 font-medium text-slate-700">{{ fileInfo.size_human }}</span>
        </div>
        <div>
          <span class="text-slate-500">Triangles:</span>
          <span class="ml-1 font-medium text-slate-700">{{ formatNumber(fileInfo.triangles) }}</span>
        </div>
        <div>
          <span class="text-slate-500">Dimensions:</span>
          <span class="ml-1 font-medium text-slate-700">
            {{ fileInfo.dimensions?.x_mm }} x {{ fileInfo.dimensions?.y_mm }} x {{ fileInfo.dimensions?.z_mm }} mm
          </span>
        </div>
      </div>
    </div>

    <!-- Primary Downloads -->
    <div class="flex flex-col sm:flex-row gap-3 mb-4">
      <a
        :href="stlUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-xl shadow-lg shadow-primary-600/25 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download STL
      </a>

      <a
        v-if="slicerAvailable"
        :href="threemfUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-white hover:bg-slate-50 text-slate-700 font-semibold border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Pre-Sliced 3MF
      </a>

      <button
        @click="$emit('print')"
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-white hover:bg-slate-50 text-slate-700 font-semibold border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Send to Printer
      </button>
    </div>

    <!-- Multi-Color Section (Collapsible) -->
    <div class="border border-slate-200 rounded-xl overflow-hidden">
      <button
        @click="showMultiColor = !showMultiColor"
        class="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors"
      >
        <div class="flex items-center gap-3">
          <div class="flex -space-x-1">
            <div class="w-4 h-4 rounded-full bg-red-500 border-2 border-white"></div>
            <div class="w-4 h-4 rounded-full bg-gray-500 border-2 border-white"></div>
            <div class="w-4 h-4 rounded-full bg-blue-500 border-2 border-white"></div>
            <div class="w-4 h-4 rounded-full bg-green-500 border-2 border-white"></div>
          </div>
          <span class="font-medium text-slate-700">Multi-Color Printing (AMS)</span>
        </div>
        <svg
          class="w-5 h-5 text-slate-400 transition-transform"
          :class="{ 'rotate-180': showMultiColor }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div v-if="showMultiColor" class="p-4 space-y-4">
        <p class="text-sm text-slate-600">
          Download individual layers to import into Bambu Studio and assign to different filament slots.
        </p>

        <!-- Layer Downloads Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
          <a
            v-for="layer in layers"
            :key="layer.id"
            :href="getLayerUrl(layer.id)"
            download
            class="flex items-center gap-2 px-3 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-sm font-medium transition-colors"
          >
            <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: layer.color }"></div>
            <span class="text-slate-700">{{ layer.name }}</span>
          </a>
        </div>

        <!-- Bambu Studio instructions -->
        <div class="text-xs text-slate-600 bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-1">
          <p class="font-semibold text-amber-800">Bambu Studio import:</p>
          <ol class="list-decimal list-inside space-y-0.5 text-slate-600">
            <li>Import first STL (Base recommended)</li>
            <li>Right-click object → <strong>Add Part</strong> → select next STL</li>
            <li>Repeat for each layer (keeps alignment)</li>
            <li>Select each part → assign to filament slot</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getDownloadUrl } from '../../api.js'

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
