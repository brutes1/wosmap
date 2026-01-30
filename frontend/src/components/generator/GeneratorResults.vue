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

    <!-- Download buttons -->
    <div class="flex flex-col sm:flex-row gap-3">
      <a
        :href="stlUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-white hover:bg-slate-50 text-slate-900 font-semibold border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download STL
      </a>

      <a
        v-if="multicolorAvailable"
        :href="multicolor3mfUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-gradient-to-r from-green-500 via-blue-500 to-red-500 hover:from-green-600 hover:via-blue-600 hover:to-red-600 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
        Multi-Color 3MF
      </a>

      <a
        v-if="slicerAvailable"
        :href="threemfUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-600 hover:to-accent-700 text-white font-semibold rounded-xl shadow-lg shadow-accent-500/25 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Pre-Sliced 3MF
      </a>

      <button
        @click="$emit('print')"
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-xl shadow-lg shadow-primary-600/25 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Send to Printer
      </button>
    </div>

    <div class="mt-4 text-xs text-slate-500 text-center space-y-1">
      <p v-if="multicolorAvailable">
        Multi-Color 3MF: parks (green), water (blue), roads (gray), buildings (red) - for AMS/multi-material printers
      </p>
      <p v-if="slicerAvailable">
        Pre-Sliced 3MF: ironing for smooth tactile surfaces (0.3mm layers, 20% ironing)
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GeneratorResults',

  props: {
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
    multicolor3mfUrl: {
      type: String,
      required: true
    },
    slicerAvailable: {
      type: Boolean,
      default: false
    },
    multicolorAvailable: {
      type: Boolean,
      default: false
    }
  },

  emits: ['print'],

  methods: {
    formatNumber(num) {
      if (num === null || num === undefined) return '-'
      return num.toLocaleString()
    }
  }
}
</script>
