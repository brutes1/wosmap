<template>
  <div class="container">
    <header>
      <h1>WOSMap</h1>
      <p class="subtitle">Create 3D-printable tactile maps for the visually impaired</p>
    </header>

    <main>
      <!-- Location Selection -->
      <section class="card">
        <h2>Location</h2>
        <MapSelector
          v-model:latitude="latitude"
          v-model:longitude="longitude"
          :scale="scale"
          :size-cm="sizeCm"
          :disabled="isProcessing"
        />
      </section>

      <!-- Print Settings -->
      <section class="card">
        <h2>Print Settings</h2>

        <div class="form-row">
          <div class="form-group">
            <label for="scale">Scale</label>
            <select id="scale" v-model.number="scale" :disabled="isProcessing">
              <option :value="1000">1:1000 (Very detailed)</option>
              <option :value="2000">1:2000</option>
              <option :value="3463">1:3463 (Default)</option>
              <option :value="5000">1:5000</option>
              <option :value="7500">1:7500</option>
              <option :value="10000">1:10000 (Wide area)</option>
            </select>
          </div>

          <div class="form-group">
            <label for="size">Print Size (cm)</label>
            <input
              id="size"
              type="number"
              min="5"
              max="50"
              step="1"
              v-model.number="sizeCm"
              :disabled="isProcessing"
            />
          </div>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="includeBuildings" :disabled="isProcessing" />
            Include buildings
          </label>
        </div>
      </section>

      <!-- Data Source -->
      <section class="card">
        <h2>Data Source</h2>
        <div class="radio-group">
          <label>
            <input type="radio" v-model="dataSource" value="osm" :disabled="isProcessing" />
            OpenStreetMap (default)
          </label>
          <label>
            <input type="radio" v-model="dataSource" value="osm_ms" :disabled="isProcessing" />
            OSM + Microsoft Buildings (better coverage)
          </label>
        </div>
      </section>

      <!-- Generate Button -->
      <button
        class="btn-primary"
        @click="generateMap"
        :disabled="isProcessing || !isValid"
      >
        {{ isProcessing ? 'Generating...' : 'Generate Map' }}
      </button>

      <!-- Status -->
      <section v-if="status" class="card status-card" :class="statusClass">
        <h3>Status</h3>
        <p class="status-message">{{ statusMessage }}</p>
        <div v-if="isProcessing" class="progress-bar">
          <div class="progress-bar-fill"></div>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </section>

      <!-- Results -->
      <section v-if="completed" class="card results-card">
        <h3>Map Ready</h3>
        <div class="button-row">
          <a :href="downloadUrl" class="btn-secondary" download>
            Download STL
          </a>
          <button class="btn-secondary" @click="showPrinterModal = true">
            Send to Printer
          </button>
        </div>
      </section>
    </main>

    <!-- Printer Configuration Modal -->
    <div v-if="showPrinterModal" class="modal-overlay" @click.self="showPrinterModal = false">
      <div class="modal">
        <h3>Configure Bambu X1C Printer</h3>
        <p class="modal-note">
          Developer Mode must be enabled on your printer.
          <a href="https://wiki.bambulab.com/en/knowledge-sharing/enable-developer-mode" target="_blank">
            Learn more
          </a>
        </p>

        <div class="form-group">
          <label for="printer-ip">Printer IP Address</label>
          <input
            id="printer-ip"
            type="text"
            v-model="printerIp"
            placeholder="192.168.1.100"
          />
        </div>

        <div class="form-group">
          <label for="printer-code">Access Code (8 digits)</label>
          <input
            id="printer-code"
            type="text"
            v-model="printerAccessCode"
            placeholder="12345678"
            maxlength="8"
          />
        </div>

        <div class="form-group">
          <label for="printer-serial">Serial Number</label>
          <input
            id="printer-serial"
            type="text"
            v-model="printerSerial"
            placeholder="00M00A000000000"
          />
        </div>

        <div class="button-row">
          <button class="btn-secondary" @click="showPrinterModal = false">
            Cancel
          </button>
          <button class="btn-primary" @click="savePrinterAndPrint">
            Save & Print
          </button>
        </div>
      </div>
    </div>

    <footer>
      <p>
        Powered by <a href="https://www.openstreetmap.org/" target="_blank">OpenStreetMap</a>
        and <a href="https://github.com/skarkkai/touch-mapper" target="_blank">touch-mapper</a>
      </p>
    </footer>
  </div>
</template>

<script>
import { createMap, getMapStatus, getDownloadUrl, configurePrinter, sendToPrinter, pollUntilComplete } from './api.js'
import MapSelector from './components/MapSelector.vue'

export default {
  name: 'App',

  components: {
    MapSelector,
  },

  data() {
    return {
      // Location (set by MapSelector)
      latitude: null,
      longitude: null,

      // Print settings
      scale: 3463,
      sizeCm: 23,
      includeBuildings: true,
      dataSource: 'osm',

      // Status
      status: null,
      error: null,
      jobId: null,
      completed: false,
      isProcessing: false,

      // Printer
      showPrinterModal: false,
      printerIp: '',
      printerAccessCode: '',
      printerSerial: '',
    }
  },

  computed: {
    isValid() {
      // Valid when we have coordinates from the map
      return this.latitude !== null && this.longitude !== null
    },

    statusMessage() {
      if (!this.status) return ''
      switch (this.status) {
        case 'queued': return 'Job queued, waiting for worker...'
        case 'processing': return 'Generating tactile map...'
        case 'completed': return 'Map generation complete!'
        case 'failed': return 'Map generation failed'
        default: return this.status
      }
    },

    statusClass() {
      return {
        'status-completed': this.status === 'completed',
        'status-failed': this.status === 'failed',
        'status-processing': this.status === 'queued' || this.status === 'processing',
      }
    },

    downloadUrl() {
      if (!this.jobId) return '#'
      return getDownloadUrl(this.jobId, 'stl')
    },
  },

  methods: {
    async generateMap() {
      this.error = null
      this.completed = false
      this.isProcessing = true
      this.status = 'queued'

      try {
        const params = {
          latitude: this.latitude,
          longitude: this.longitude,
          scale: this.scale,
          size_cm: this.sizeCm,
          include_buildings: this.includeBuildings,
          data_source: this.dataSource,
        }

        // Submit job
        const response = await createMap(params)
        this.jobId = response.job_id

        // Poll for completion
        const result = await pollUntilComplete(this.jobId)
        this.status = 'completed'
        this.completed = true

      } catch (err) {
        this.status = 'failed'
        this.error = err.message
      } finally {
        this.isProcessing = false
      }
    },

    async savePrinterAndPrint() {
      try {
        await configurePrinter({
          ip: this.printerIp,
          access_code: this.printerAccessCode,
          serial: this.printerSerial,
        })

        const result = await sendToPrinter(this.jobId)
        alert(result.message || 'Print job sent!')
        this.showPrinterModal = false

      } catch (err) {
        alert('Failed to send to printer: ' + err.message)
      }
    },
  },
}
</script>

<style>
.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}

header {
  text-align: center;
  margin-bottom: 30px;
}

header h1 {
  color: #333;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card h2 {
  font-size: 16px;
  color: #333;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: #555;
  margin-bottom: 6px;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group select:focus {
  outline: none;
  border-color: #4a90d9;
}

.form-group input[type="checkbox"],
.form-group input[type="radio"] {
  margin-right: 8px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.radio-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
}

.btn-primary {
  display: block;
  width: 100%;
  padding: 14px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #3a7bc8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: white;
  color: #4a90d9;
  border: 2px solid #4a90d9;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #4a90d9;
  color: white;
}

.button-row {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.status-card {
  margin-top: 20px;
}

.status-card h3 {
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
}

.status-message {
  font-size: 14px;
  color: #666;
}

.status-processing {
  border-left: 4px solid #4a90d9;
}

.status-completed {
  border-left: 4px solid #28a745;
}

.status-failed {
  border-left: 4px solid #dc3545;
}

.progress-bar {
  height: 4px;
  background: #eee;
  border-radius: 2px;
  margin-top: 12px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #4a90d9;
  width: 100%;
  animation: progress 1.5s ease-in-out infinite;
}

@keyframes progress {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.error {
  color: #dc3545;
  font-size: 14px;
  margin-top: 8px;
}

.results-card {
  text-align: center;
  background: #f8fff8;
  border: 1px solid #28a745;
}

.results-card h3 {
  color: #28a745;
  margin-bottom: 16px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 24px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
}

.modal h3 {
  margin-bottom: 8px;
}

.modal-note {
  font-size: 12px;
  color: #666;
  margin-bottom: 16px;
}

.modal-note a {
  color: #4a90d9;
}

footer {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 12px;
}

footer a {
  color: #666;
}
</style>
