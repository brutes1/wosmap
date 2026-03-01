<template>
  <div class="bg-surface-1 rounded-2xl border border-white/[0.06] overflow-hidden">
    <!-- Header (always visible, clickable to toggle) -->
    <div
      @click="expanded = !expanded"
      class="flex justify-between items-center p-4 sm:p-6 cursor-pointer hover:bg-surface-2 transition-colors"
    >
      <h2 class="text-lg font-display font-bold text-white">
        History
        <span class="text-white/30 font-sans font-normal text-sm">({{ jobs.length }})</span>
      </h2>
      <svg
        class="w-5 h-5 text-white/40 transition-transform"
        :class="{ 'rotate-180': expanded }"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </div>

    <!-- Content (collapsible) -->
    <div v-if="expanded" class="border-t border-white/[0.06]">
      <!-- Empty state -->
      <div v-if="jobs.length === 0" class="p-8 text-center text-white/25">
        No maps generated yet
      </div>

      <!-- Job list -->
      <div v-else class="p-4 sm:p-6 space-y-3">
        <div
          v-for="job in jobs"
          :key="job.job_id"
          class="flex flex-col sm:flex-row sm:items-center gap-3 p-4 bg-navy-950/50 rounded-xl"
        >
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-white truncate">{{ job.location_name }}</p>
            <p class="text-sm text-white/40">{{ formatDate(job.created_at) }}</p>
          </div>

          <div class="flex items-center gap-2 text-sm text-white/50">
            <span>{{ job.file_info?.size_human }}</span>
            <span class="text-white/20">|</span>
            <span>{{ formatNumber(job.file_info?.triangles) }} triangles</span>
          </div>

          <div class="flex gap-2">
            <a
              :href="getStlUrl(job.job_id)"
              download
              class="px-3 py-1.5 bg-primary-600 hover:bg-primary-500 text-navy-950 text-sm font-medium rounded-lg transition-colors"
            >
              STL
            </a>
            <a
              v-if="slicerAvailable"
              :href="get3mfUrl(job.job_id)"
              download
              class="px-3 py-1.5 bg-surface-2 hover:bg-surface-3 text-white/80 text-sm font-medium rounded-lg border border-white/[0.06] transition-colors"
            >
              3MF
            </a>
          </div>
        </div>

        <!-- Clear button -->
        <button
          @click="handleClear"
          class="w-full mt-4 px-4 py-2.5 text-danger-400 hover:text-danger-500 hover:bg-danger-500/10 font-medium rounded-xl border border-danger-500/20 transition-colors"
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

  emits: ['clear'],

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
