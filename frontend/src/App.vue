<template>
  <div class="h-screen flex flex-col bg-slate-100">
    <AppHeader />

    <div class="flex-1 flex flex-col md:flex-row overflow-hidden">
      <!-- Sidebar -->
      <aside class="w-full md:w-80 lg:w-96 flex-shrink-0 overflow-y-auto border-r border-slate-200 bg-white">
        <div class="p-4 space-y-4">
          <!-- Location Selection -->
          <LocationSection
            v-model:latitude="latitude"
            v-model:longitude="longitude"
            :scale="scale"
            :size-cm="sizeCm"
            :disabled="isProcessing"
          />

          <!-- Print Settings -->
          <PrintSettings
            v-model:scale="scale"
            v-model:size-cm="sizeCm"
            v-model:include-buildings="includeBuildings"
            v-model:data-source="dataSource"
            :disabled="isProcessing"
          />

          <!-- Generate Button -->
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

          <!-- History -->
          <HistoryList
            :jobs="history"
            :slicer-available="slicerAvailable"
            @clear="clearAllHistory"
          />
        </div>
      </aside>

      <!-- Preview Panel -->
      <main class="flex-1 flex flex-col min-w-0 bg-slate-50">
        <!-- 3D Viewer -->
        <div class="flex-1 relative min-h-[300px] md:min-h-0">
          <StlViewer
            v-if="completed && downloadUrl"
            :stl-url="downloadUrl"
            @load="onModelLoaded"
            @error="onModelError"
          />
          <EmptyState v-else />
        </div>

        <!-- Download Bar (when complete) -->
        <GeneratorResults
          v-if="completed"
          class="border-t border-slate-200"
          :file-info="fileInfo"
          :stl-url="downloadUrl"
          :threemf-url="download3mfUrl"
          :slicer-available="slicerAvailable"
          @print="showPrinterModal = true"
        />
      </main>
    </div>

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
import LocationSection from './components/location/LocationSection.vue'
import PrintSettings from './components/settings/PrintSettings.vue'
import GenerateButton from './components/generator/GenerateButton.vue'
import GeneratorProgress from './components/generator/GeneratorProgress.vue'
import GeneratorResults from './components/generator/GeneratorResults.vue'
import HistoryList from './components/history/HistoryList.vue'
import PrinterModal from './components/printer/PrinterModal.vue'
import StlViewer from './components/viewer/StlViewer.vue'
import EmptyState from './components/viewer/EmptyState.vue'

export default {
  name: 'App',

  components: {
    AppHeader,
    LocationSection,
    PrintSettings,
    GenerateButton,
    GeneratorProgress,
    GeneratorResults,
    HistoryList,
    PrinterModal,
    StlViewer,
    EmptyState
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
      if (!this.jobId) return null
      return getDownloadUrl(this.jobId, 'stl')
    },

    download3mfUrl() {
      if (!this.jobId) return null
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
    },

    onModelLoaded(info) {
      console.log('3D model loaded:', info.triangles, 'triangles')
    },

    onModelError(err) {
      console.error('Failed to load 3D model:', err)
    }
  }
}
</script>
