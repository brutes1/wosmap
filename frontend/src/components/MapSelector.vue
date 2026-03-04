<template>
  <div class="w-full bg-surface-1 rounded-2xl border border-white/[0.06] overflow-hidden">
    <!-- Hero Search Section -->
    <div class="px-4 sm:px-6 py-4 sm:py-5 border-b border-white/[0.06]">
      <p class="text-sm font-medium text-white/50 mb-2.5">Find your place</p>
      <div class="flex gap-2">
        <div class="flex-1 relative">
          <span class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-white/30">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </span>
          <input
            type="text"
            v-model="searchQuery"
            @keyup.enter="searchAddress"
            placeholder="Enter an address or place..."
            :disabled="disabled || isSearching"
            class="w-full pl-10 pr-4 py-3 bg-surface-2 border border-white/[0.08] rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
        <button
          type="button"
          @click="searchAddress"
          :disabled="disabled || isSearching || !searchQuery.trim()"
          class="px-5 py-3 bg-primary-600 hover:bg-primary-500 text-navy-950 font-medium rounded-xl text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary-600 whitespace-nowrap"
        >
          {{ isSearching ? '...' : 'Search' }}
        </button>
      </div>
      <p v-if="searchError" class="mt-2 text-sm text-danger-400">{{ searchError }}</p>
    </div>

    <!-- Map Container -->
    <div class="h-[320px] sm:h-[380px] md:h-[460px] lg:h-[560px] relative">
      <div ref="mapContainer" class="w-full h-full"></div>
      <!-- Overlay when disabled: dims and blocks interactions without touching Leaflet's container -->
      <div v-if="disabled" class="absolute inset-0 bg-navy-950/30"></div>
    </div>

    <!-- Coordinates Display -->
    <div class="flex justify-between items-center px-4 sm:px-6 py-2.5 bg-navy-950/40 border-t border-white/[0.06] text-sm">
      <span v-if="hasMarker" class="text-white/60 font-mono text-xs">
        {{ latitude?.toFixed(5) }}, {{ longitude?.toFixed(5) }}
      </span>
      <span v-else class="text-white/25 italic text-xs">
        Click on the map to select a point
      </span>
      <button
        v-if="hasMarker"
        type="button"
        @click="resetMarker"
        :disabled="disabled"
        class="px-3 py-1 text-xs font-medium text-danger-400 hover:text-danger-500 hover:bg-danger-500/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
      searchError: null,
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
        } else {
          this.map.dragging.enable()
          this.map.touchZoom.enable()
          this.map.doubleClickZoom.enable()
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
        scrollWheelZoom: false,
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

      this.rectangle = L.rectangle(bounds, {
        color: '#d4a053',
        fillColor: '#d4a053',
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
      this.searchError = null
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
          this.searchError = 'Address not found. Try a different search.'
        }
      } catch (err) {
        console.error('Geocoding error:', err)
        this.searchError = 'Search failed. Please check your connection and try again.'
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
