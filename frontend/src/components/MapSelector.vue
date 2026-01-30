<template>
  <div class="w-full h-full flex flex-col">
    <!-- Address Search -->
    <div class="flex gap-2 p-3 sm:p-4 bg-slate-50 border-b border-slate-100">
      <input
        type="text"
        v-model="searchQuery"
        @keyup.enter="searchAddress"
        placeholder="Search for an address..."
        :disabled="disabled || isSearching"
        class="flex-1 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="button"
        @click="searchAddress"
        :disabled="disabled || isSearching || !searchQuery.trim()"
        class="px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary-600 whitespace-nowrap"
      >
        {{ isSearching ? '...' : 'Search' }}
      </button>
    </div>

    <!-- Map Container -->
    <div
      ref="mapContainer"
      class="flex-1 min-h-0"
      :class="{ 'opacity-70 pointer-events-none': disabled }"
    ></div>

    <!-- Coordinates Display -->
    <div class="flex justify-between items-center px-3 sm:px-4 py-2.5 bg-slate-50 border-t border-slate-100 text-sm">
      <span v-if="hasMarker" class="text-slate-700 font-mono">
        {{ latitude?.toFixed(5) }}, {{ longitude?.toFixed(5) }}
      </span>
      <span v-else class="text-slate-400 italic">
        Click on the map to select a point
      </span>
      <button
        v-if="hasMarker"
        type="button"
        @click="resetMarker"
        :disabled="disabled"
        class="px-3 py-1 text-xs font-medium text-danger-600 hover:text-danger-700 hover:bg-danger-500/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
      rectangle: null,
      searchQuery: '',
      isSearching: false,
      resizeObserver: null,
    }
  },

  computed: {
    hasMarker() {
      return this.latitude !== null && this.longitude !== null
    },

    coverageHalfSide() {
      const sideMeters = (this.sizeCm * this.scale) / 100
      return sideMeters / 2
    },
  },

  watch: {
    coverageHalfSide() {
      this.updateRectangle()
    },

    latitude() {
      this.syncMarkerFromProps()
    },
    longitude() {
      this.syncMarkerFromProps()
    },

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
        // Invalidate size after state change causes layout reflow
        this.$nextTick(() => {
          this.map.invalidateSize()
        })
      }
    },
  },

  mounted() {
    this.initMap()

    // Watch for container resize and invalidate map
    this.resizeObserver = new ResizeObserver(() => {
      if (this.map) {
        this.map.invalidateSize()
      }
    })
    this.resizeObserver.observe(this.$refs.mapContainer)
  },

  beforeUnmount() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
    }
    if (this.map) {
      this.map.remove()
    }
  },

  methods: {
    initMap() {
      let center = [40, -95]
      let zoom = 4

      if (this.hasMarker) {
        center = [this.latitude, this.longitude]
        zoom = 14
      }

      this.map = L.map(this.$refs.mapContainer, {
        center,
        zoom,
        zoomControl: true,
      })

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(this.map)

      this.map.on('click', this.onMapClick)

      if (this.hasMarker) {
        this.setMarker(this.latitude, this.longitude)
      }

      if (!this.hasMarker) {
        this.tryGeolocation()
      }

      // Invalidate size after a short delay to handle flex layout sizing
      setTimeout(() => {
        if (this.map) {
          this.map.invalidateSize()
        }
      }, 100)
    },

    onMapClick(e) {
      if (this.disabled) return

      const { lat, lng } = e.latlng
      this.setMarker(lat, lng)
      this.$emit('update:latitude', lat)
      this.$emit('update:longitude', lng)
    },

    setMarker(lat, lng) {
      if (this.marker) {
        this.map.removeLayer(this.marker)
      }

      this.marker = L.marker([lat, lng], { draggable: !this.disabled })
        .addTo(this.map)

      this.marker.on('dragend', (e) => {
        const pos = e.target.getLatLng()
        this.$emit('update:latitude', pos.lat)
        this.$emit('update:longitude', pos.lng)
        this.updateRectangle()
      })

      this.updateRectangle()
    },

    metersToLatDegrees(meters) {
      return meters / 111320
    },

    metersToLngDegrees(meters, lat) {
      return meters / (111320 * Math.cos(lat * Math.PI / 180))
    },

    updateRectangle() {
      if (!this.hasMarker || !this.map) return

      if (this.rectangle) {
        this.map.removeLayer(this.rectangle)
      }

      const halfSide = this.coverageHalfSide
      const latOffset = this.metersToLatDegrees(halfSide)
      const lngOffset = this.metersToLngDegrees(halfSide, this.latitude)

      const bounds = [
        [this.latitude - latOffset, this.longitude - lngOffset],
        [this.latitude + latOffset, this.longitude + lngOffset]
      ]

      // Use a vibrant primary color for the rectangle
      this.rectangle = L.rectangle(bounds, {
        color: '#3b82f6',
        fillColor: '#3b82f6',
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
        this.updateRectangle()
      } else if (this.marker) {
        this.map.removeLayer(this.marker)
        this.marker = null
        if (this.rectangle) {
          this.map.removeLayer(this.rectangle)
          this.rectangle = null
        }
      }
    },

    resetMarker() {
      if (this.marker) {
        this.map.removeLayer(this.marker)
        this.marker = null
      }
      if (this.rectangle) {
        this.map.removeLayer(this.rectangle)
        this.rectangle = null
      }
      this.$emit('update:latitude', null)
      this.$emit('update:longitude', null)
    },

    async searchAddress() {
      if (!this.searchQuery.trim() || this.isSearching) return

      this.isSearching = true
      try {
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

          this.setMarker(latitude, longitude)
          this.$emit('update:latitude', latitude)
          this.$emit('update:longitude', longitude)

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
