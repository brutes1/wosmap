<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
    <AppHeader />

    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <!-- Location Selection -->
      <section class="mb-6">
        <LocationSection
          v-model:latitude="latitude"
          v-model:longitude="longitude"
          :scale="scale"
          :size-cm="sizeCm"
          :disabled="isProcessing"
        />
      </section>

      <!-- Settings and Generate Button -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div class="lg:col-span-2">
          <PrintSettings
            v-model:scale="scale"
            v-model:size-cm="sizeCm"
            v-model:include-buildings="includeBuildings"
            v-model:data-source="dataSource"
            :disabled="isProcessing"
          />
        </div>
        <div class="lg:col-span-1 flex items-end">
          <GenerateButton
            @click="generateMap"
            :disabled="!isValid"
            :loading="isProcessing"
          />
        </div>
      </div>

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
      includeBuildings: true,
      dataSource: 'overture',

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
        const params = {
          latitude: this.latitude,
          longitude: this.longitude,
          scale: this.scale,
          size_cm: this.sizeCm,
          include_buildings: this.includeBuildings,
          data_source: this.dataSource
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
