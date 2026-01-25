<template>
  <div class="map-selector">
    <!-- Address Search -->
    <div class="search-bar">
      <input
        type="text"
        v-model="searchQuery"
        @keyup.enter="searchAddress"
        placeholder="Search for an address..."
        :disabled="disabled || isSearching"
      />
      <button
        type="button"
        @click="searchAddress"
        :disabled="disabled || isSearching || !searchQuery.trim()"
        class="search-btn"
      >
        {{ isSearching ? '...' : 'Search' }}
      </button>
    </div>

    <!-- Map Container -->
    <div
      ref="mapContainer"
      class="map-container"
      :class="{ disabled: disabled }"
    ></div>

    <!-- Coordinates Display -->
    <div class="coordinates-bar">
      <span v-if="hasMarker" class="coords">
        Center: {{ latitude?.toFixed(5) }}, {{ longitude?.toFixed(5) }}
      </span>
      <span v-else class="hint">Click on the map to select center point</span>
      <button
        v-if="hasMarker"
        type="button"
        @click="resetMarker"
        :disabled="disabled"
        class="reset-btn"
      >
        Reset
      </button>
    </div>
  </div>
</template>

<script>
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

export default {
  name: 'MapSelector',

  props: {
    latitude: {
      type: Number,
      default: null,
    },
    longitude: {
      type: Number,
      default: null,
    },
    scale: {
      type: Number,
      required: true,
    },
    sizeCm: {
      type: Number,
      required: true,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['update:latitude', 'update:longitude'],

  data() {
    return {
      map: null,
      marker: null,
      circle: null,
      searchQuery: '',
      isSearching: false,
    }
  },

  computed: {
    hasMarker() {
      return this.latitude !== null && this.longitude !== null
    },

    // Coverage radius in meters
    coverageRadius() {
      // diameter = sizeCm * scale / 100 (converts cm at scale to meters)
      const diameterMeters = (this.sizeCm * this.scale) / 100
      return diameterMeters / 2
    },
  },

  watch: {
    // Update circle when scale or size changes
    coverageRadius() {
      this.updateCircle()
    },

    // Update marker when coords change externally
    latitude() {
      this.syncMarkerFromProps()
    },
    longitude() {
      this.syncMarkerFromProps()
    },

    // Disable map interactions when disabled
    disabled(newVal) {
      if (this.map) {
        if (newVal) {
          this.map.dragging.disable()
          this.map.touchZoom.disable()
          this.map.doubleClickZoom.disable()
          this.map.scrollWheelZoom.disable()
        } else {
          this.map.dragging.enable()
          this.map.touchZoom.enable()
          this.map.doubleClickZoom.enable()
          this.map.scrollWheelZoom.enable()
        }
      }
    },
  },

  mounted() {
    this.initMap()
  },

  beforeUnmount() {
    if (this.map) {
      this.map.remove()
    }
  },

  methods: {
    initMap() {
      // Default center (world view, or use existing coords if set)
      let center = [40, -95]  // Roughly center of US
      let zoom = 4

      if (this.hasMarker) {
        center = [this.latitude, this.longitude]
        zoom = 14
      }

      // Create map
      this.map = L.map(this.$refs.mapContainer, {
        center,
        zoom,
        zoomControl: true,
      })

      // Add OpenStreetMap tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(this.map)

      // Handle click to set marker
      this.map.on('click', this.onMapClick)

      // If we already have coords, set up the marker
      if (this.hasMarker) {
        this.setMarker(this.latitude, this.longitude)
      }

      // Try geolocation on first load if no coords set
      if (!this.hasMarker) {
        this.tryGeolocation()
      }
    },

    onMapClick(e) {
      if (this.disabled) return

      const { lat, lng } = e.latlng
      this.setMarker(lat, lng)
      this.$emit('update:latitude', lat)
      this.$emit('update:longitude', lng)
    },

    setMarker(lat, lng) {
      // Remove existing marker
      if (this.marker) {
        this.map.removeLayer(this.marker)
      }

      // Create new draggable marker
      this.marker = L.marker([lat, lng], { draggable: !this.disabled })
        .addTo(this.map)

      // Handle marker drag
      this.marker.on('dragend', (e) => {
        const pos = e.target.getLatLng()
        this.$emit('update:latitude', pos.lat)
        this.$emit('update:longitude', pos.lng)
        this.updateCircle()
      })

      // Update circle
      this.updateCircle()
    },

    updateCircle() {
      if (!this.hasMarker || !this.map) return

      // Remove existing circle
      if (this.circle) {
        this.map.removeLayer(this.circle)
      }

      // Create new circle showing coverage area
      this.circle = L.circle([this.latitude, this.longitude], {
        radius: this.coverageRadius,
        color: '#4a90d9',
        fillColor: '#4a90d9',
        fillOpacity: 0.15,
        weight: 2,
      }).addTo(this.map)
    },

    syncMarkerFromProps() {
      if (!this.map) return

      if (this.hasMarker) {
        if (this.marker) {
          this.marker.setLatLng([this.latitude, this.longitude])
        } else {
          this.setMarker(this.latitude, this.longitude)
        }
        this.updateCircle()
      } else if (this.marker) {
        this.map.removeLayer(this.marker)
        this.marker = null
        if (this.circle) {
          this.map.removeLayer(this.circle)
          this.circle = null
        }
      }
    },

    resetMarker() {
      if (this.marker) {
        this.map.removeLayer(this.marker)
        this.marker = null
      }
      if (this.circle) {
        this.map.removeLayer(this.circle)
        this.circle = null
      }
      this.$emit('update:latitude', null)
      this.$emit('update:longitude', null)
    },

    async searchAddress() {
      if (!this.searchQuery.trim() || this.isSearching) return

      this.isSearching = true
      try {
        // Use Nominatim for geocoding (same as backend)
        const query = encodeURIComponent(this.searchQuery)
        const response = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${query}&format=json&limit=1`,
          {
            headers: {
              'User-Agent': 'TactileMapGenerator/1.0',
            },
          }
        )
        const results = await response.json()

        if (results.length > 0) {
          const { lat, lon } = results[0]
          const latitude = parseFloat(lat)
          const longitude = parseFloat(lon)

          // Set marker and emit
          this.setMarker(latitude, longitude)
          this.$emit('update:latitude', latitude)
          this.$emit('update:longitude', longitude)

          // Pan to location
          this.map.setView([latitude, longitude], 15)
        } else {
          alert('Address not found. Try a different search.')
        }
      } catch (err) {
        console.error('Geocoding error:', err)
        alert('Search failed. Please try again.')
      } finally {
        this.isSearching = false
      }
    },

    tryGeolocation() {
      if (!navigator.geolocation) return

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords
          // Just center the map, don't set marker (user should click to confirm)
          this.map.setView([latitude, longitude], 14)
        },
        () => {
          // Geolocation denied or failed, stay at default view
        },
        { timeout: 5000 }
      )
    },
  },
}
</script>

<style scoped>
.map-selector {
  width: 100%;
}

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-bar input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.search-bar input:focus {
  outline: none;
  border-color: #4a90d9;
}

.search-btn {
  padding: 10px 16px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}

.search-btn:hover:not(:disabled) {
  background: #3a7bc8;
}

.search-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.map-container {
  height: 300px;
  border-radius: 6px;
  border: 1px solid #ddd;
  overflow: hidden;
}

.map-container.disabled {
  opacity: 0.7;
  pointer-events: none;
}

.coordinates-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 13px;
}

.coords {
  color: #333;
  font-family: monospace;
}

.hint {
  color: #888;
  font-style: italic;
}

.reset-btn {
  padding: 4px 12px;
  background: transparent;
  color: #666;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.reset-btn:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: #999;
}

.reset-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
