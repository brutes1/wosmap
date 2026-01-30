<template>
  <div class="bg-white rounded-2xl shadow-lg shadow-slate-900/5 border border-slate-100 overflow-hidden mt-6">
    <!-- Header (always visible, clickable to toggle) -->
    <div
      @click="expanded = !expanded"
      class="flex justify-between items-center p-4 sm:p-6 cursor-pointer hover:bg-slate-50 transition-colors"
    >
      <h2 class="text-xl font-bold text-slate-900">
        History
        <span class="text-slate-400 font-normal">({{ jobs.length }})</span>
      </h2>
      <svg
        class="w-5 h-5 text-slate-400 transition-transform"
        :class="{ 'rotate-180': expanded }"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </div>

    <!-- Content (collapsible) -->
    <div v-if="expanded" class="border-t border-slate-100">
      <!-- Empty state -->
      <div v-if="jobs.length === 0" class="p-8 text-center text-slate-400">
        No maps generated yet
      </div>

      <!-- Job list -->
      <div v-else class="p-4 sm:p-6 space-y-3">
        <div
          v-for="job in jobs"
          :key="job.job_id"
          class="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-slate-50 rounded-xl"
        >
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-slate-800 truncate">{{ job.location_name }}</p>
            <p class="text-sm text-slate-500">{{ formatDate(job.created_at) }}</p>
          </div>

          <div class="flex items-center gap-2 text-sm text-slate-500">
            <span>{{ job.file_info?.size_human }}</span>
            <span class="text-slate-300">|</span>
            <span>{{ formatNumber(job.file_info?.triangles) }} triangles</span>
          </div>

          <div class="flex gap-2">
            <button
              @click="$emit('preview', job)"
              class="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm font-medium rounded-lg transition-colors"
              title="Preview in 3D viewer"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
            <a
              :href="getStlUrl(job.job_id)"
              download
              class="px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              STL
            </a>
            <a
              v-if="slicerAvailable"
              :href="get3mfUrl(job.job_id)"
              download
              class="px-3 py-1.5 bg-accent-500 hover:bg-accent-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              3MF
            </a>
          </div>
        </div>

        <!-- Clear button -->
        <button
          @click="handleClear"
          class="w-full mt-4 px-4 py-2.5 text-danger-600 hover:text-danger-700 hover:bg-danger-500/10 font-medium rounded-xl border border-danger-200 transition-colors"
        >
          Clear All History
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { getDownloadUrl } from '../../api.js'

export default {
  name: 'HistoryList',

  props: {
    jobs: {
      type: Array,
      default: () => []
    },
    slicerAvailable: {
      type: Boolean,
      default: false
    }
  },

  emits: ['clear', 'preview'],

  data() {
    return {
      expanded: false
    }
  },

  methods: {
    formatDate(isoString) {
      if (!isoString) return ''
      const date = new Date(isoString)
      return date.toLocaleDateString()
    },

    formatNumber(num) {
      if (num === null || num === undefined) return '-'
      return num.toLocaleString()
    },

    getStlUrl(jobId) {
      return getDownloadUrl(jobId, 'stl')
    },

    get3mfUrl(jobId) {
      return getDownloadUrl(jobId, '3mf')
    },

    handleClear() {
      if (confirm('Delete all generated maps? This cannot be undone.')) {
        this.$emit('clear')
      }
    }
  }
}
</script>
