<template>
  <div class="bg-white p-4">
    <div class="flex flex-col sm:flex-row sm:items-center gap-4">
      <!-- File info (compact) -->
      <div v-if="fileInfo" class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-full bg-success-500 flex items-center justify-center flex-shrink-0">
            <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div class="min-w-0">
            <p class="font-semibold text-slate-800 text-sm truncate">{{ fileInfo.filename }}</p>
            <p class="text-xs text-slate-500">
              {{ fileInfo.size_human }} &middot; {{ formatNumber(fileInfo.triangles) }} triangles
            </p>
          </div>
        </div>
      </div>

      <!-- Download buttons (compact) -->
      <div class="flex flex-wrap gap-2">
        <a
          :href="stlUrl"
          download
          class="flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 font-medium text-sm border border-slate-200 rounded-lg transition-colors"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          STL
        </a>

        <a
          v-if="slicerAvailable"
          :href="threemfUrl"
          download
          class="flex items-center gap-2 px-4 py-2 bg-accent-500 hover:bg-accent-600 text-white font-medium text-sm rounded-lg transition-colors"
          title="Pre-sliced with ironing for smooth tactile surfaces"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          3MF
        </a>

        <button
          @click="$emit('print')"
          class="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm rounded-lg transition-colors"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Print
        </button>
      </div>
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
