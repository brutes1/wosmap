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
        v-if="slicerAvailable"
        :href="threemfUrl"
        download
        class="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-600 hover:to-accent-700 text-white font-semibold rounded-xl shadow-lg shadow-accent-500/25 transition-all"
      >
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Download 3MF
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

    <p v-if="slicerAvailable" class="mt-4 text-xs text-slate-500 text-center">
      3MF is pre-sliced with ironing for smooth tactile surfaces (0.3mm layers, 20% ironing)
    </p>
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
    slicerAvailable: {
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
