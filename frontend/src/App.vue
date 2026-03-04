<template>
  <div class="min-h-screen bg-navy-950">
    <AppHeader />

    <main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-6">
      <!-- Location Selection -->
      <LocationSection
        v-model:latitude="latitude"
        v-model:longitude="longitude"
        :scale="scale"
        :size-cm="sizeCm"
        :disabled="isProcessing"
      />

      <!-- Print Settings (compact row) -->
      <PrintSettings
        v-model:scale="scale"
        v-model:size-cm="sizeCm"
        :disabled="isProcessing"
      />

      <!-- Map Layers (collapsible) -->
      <details class="group bg-surface-1 rounded-2xl border border-white/[0.06] overflow-hidden">
        <summary class="px-4 sm:px-6 py-4 cursor-pointer flex items-center justify-between text-white/60 hover:text-white/90 transition-colors select-none list-none">
          <span class="text-sm font-medium">Map Layers</span>
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div class="border-t border-white/[0.06]">
          <LayerSettings
            v-model="layers"
            :disabled="isProcessing"
          />
        </div>
      </details>

      <!-- Data Source Toggle -->
      <div class="flex items-center justify-center gap-3 py-3">
        <span class="text-sm font-medium text-white/50">Data source</span>
        <div class="flex rounded-lg overflow-hidden border border-white/[0.08]">
          <button
            type="button"
            @click="dataSource = 'osm'"
            :disabled="isProcessing"
            class="px-4 py-2 text-sm font-medium transition-all disabled:opacity-50"
            :class="dataSource === 'osm'
              ? 'bg-primary-600 text-navy-950'
              : 'bg-surface-1 text-white/60 hover:bg-surface-2 hover:text-white/80'"
          >
            OpenStreetMap
          </button>
          <button
            type="button"
            @click="dataSource = 'overture'"
            :disabled="isProcessing"
            class="px-4 py-2 text-sm font-medium transition-all disabled:opacity-50"
            :class="dataSource === 'overture'
              ? 'bg-primary-600 text-navy-950'
              : 'bg-surface-1 text-white/60 hover:bg-surface-2 hover:text-white/80'"
          >
            Overture Maps
          </button>
        </div>
      </div>

      <!-- Generate Button (full-width) -->
      <GenerateButton
        @click="generateMap"
        :disabled="!isValid"
        :loading="isProcessing"
      />

      <!-- Progress (while generating) -->
      <GeneratorProgress
        v-if="isProcessing"
        :stages="stages"
        :current-stage="currentStage"
        :stage-message="stageMessage"
        :error="error"
      />

      <!-- Results (when complete) -->
      <GeneratorResults
        v-if="completed"
        :job-id="jobId"
        :file-info="fileInfo"
        :stl-url="downloadUrl"
        :threemf-url="download3mfUrl"
        :slicer-available="slicerAvailable"
        @print="showPrinterModal = true"
      />

      <!-- History -->
      <HistoryList
        :jobs="history"
        :slicer-available="slicerAvailable"
        @clear="clearAllHistory"
      />
    </main>

    <AppFooter />

    <!-- Printer Modal -->
    <PrinterModal
      :show="showPrinterModal"
      @close="showPrinterModal = false"
      @submit="savePrinterAndPrint"
    />
  </div>
</template>

<script>
import { createMap, getDownloadUrl, configurePrinter, sendToPrinter, pollUntilComplete, getHistory, clearHistory } from './api.js'

import AppHeader from './components/layout/AppHeader.vue'
import AppFooter from './components/layout/AppFooter.vue'
import LocationSection from './components/location/LocationSection.vue'
import PrintSettings from './components/settings/PrintSettings.vue'
import LayerSettings from './components/settings/LayerSettings.vue'
import GenerateButton from './components/generator/GenerateButton.vue'
import GeneratorProgress from './components/generator/GeneratorProgress.vue'
import GeneratorResults from './components/generator/GeneratorResults.vue'
import HistoryList from './components/history/HistoryList.vue'
import PrinterModal from './components/printer/PrinterModal.vue'

export default {
  name: 'App',

  components: {
    AppHeader,
    AppFooter,
    LocationSection,
    PrintSettings,
    LayerSettings,
    GenerateButton,
    GeneratorProgress,
    GeneratorResults,
    HistoryList,
    PrinterModal
  },

  data() {
    return {
      // Location
      latitude: null,
      longitude: null,

      // Print settings
      scale: 3463,
      sizeCm: 23,
      dataSource: 'overture',

      // Map layers
      layers: {
        buildings: true,
        roads: true,
        water: true,
        rivers: false,
        parks: false,
        trails: false,
        terrain: false,
      },

      // Status
      status: null,
      error: null,
      jobId: null,
      completed: false,
      isProcessing: false,
      currentStage: null,
      stageMessage: null,
      fileInfo: null,

      // Processing stages
      stages: [
        { id: 'queued', label: 'Queued' },
        { id: 'fetching_osm', label: 'Fetching OSM' },
        { id: 'fetching_overture', label: 'Fetching Overture' },
        { id: 'converting', label: 'Converting' },
        { id: 'finalizing', label: 'Finalizing' }
      ],

      // Printer
      showPrinterModal: false,

      // History
      history: [],

      // Capabilities
      slicerAvailable: false
    }
  },

  async mounted() {
    await Promise.all([
      this.loadHistory(),
      this.loadCapabilities()
    ])
  },

  computed: {
    isValid() {
      return this.latitude !== null && this.longitude !== null
    },

    downloadUrl() {
      if (!this.jobId) return '#'
      return getDownloadUrl(this.jobId, 'stl')
    },

    download3mfUrl() {
      if (!this.jobId) return '#'
      return getDownloadUrl(this.jobId, '3mf')
    }
  },

  methods: {
    async generateMap() {
      this.error = null
      this.completed = false
      this.isProcessing = true
      this.status = 'queued'
      this.currentStage = 'queued'
      this.stageMessage = null
      this.fileInfo = null

      try {
        const sizeCm = Math.min(Math.max(this.sizeCm, 5), 25.6)
        const params = {
          latitude: this.latitude,
          longitude: this.longitude,
          scale: this.scale,
          size_cm: sizeCm,
          data_source: this.dataSource,
          layers: this.layers
        }

        const response = await createMap(params)
        this.jobId = response.job_id

        const result = await pollUntilComplete(this.jobId, (statusData) => {
          this.status = statusData.status
          this.currentStage = statusData.status
          this.stageMessage = statusData.stage_message
        })

        this.status = 'completed'
        this.completed = true
        this.fileInfo = result.file_info

        await this.loadHistory()
      } catch (err) {
        this.status = 'failed'
        this.error = err.message
      } finally {
        this.isProcessing = false
      }
    },

    async loadCapabilities() {
      try {
        const response = await fetch('/api/capabilities')
        const data = await response.json()
        this.slicerAvailable = data.slicer_available
      } catch (err) {
        console.error('Failed to load capabilities:', err)
        this.slicerAvailable = false
      }
    },

    async loadHistory() {
      try {
        const result = await getHistory()
        this.history = result.jobs.filter(j => j.status === 'completed')
      } catch (err) {
        console.error('Failed to load history:', err)
      }
    },

    async clearAllHistory() {
      try {
        await clearHistory()
        this.history = []
      } catch (err) {
        alert('Failed to clear history: ' + err.message)
      }
    },

    async savePrinterAndPrint(printerConfig) {
      try {
        await configurePrinter(printerConfig)

        const result = await sendToPrinter(this.jobId)
        alert(result.message || 'Print job sent!')
        this.showPrinterModal = false
      } catch (err) {
        alert('Failed to send to printer: ' + err.message)
      }
    }
  }
}
</script>
