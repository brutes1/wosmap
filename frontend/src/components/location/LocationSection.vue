<template>
  <div class="bg-white rounded-2xl shadow-lg shadow-slate-900/5 border border-slate-100 overflow-hidden">
    <div class="p-4 sm:p-6 border-b border-slate-100">
      <h2 class="text-xl font-bold text-slate-900">Select Location</h2>
      <p class="text-sm text-slate-500 mt-1">Search for an address or click on the map</p>
    </div>

    <div class="h-[300px] sm:h-[350px] md:h-[400px] lg:h-[450px]">
      <MapSelector
        v-model:latitude="internalLat"
        v-model:longitude="internalLng"
        :scale="scale"
        :size-cm="sizeCm"
        :disabled="disabled"
      />
    </div>
  </div>
</template>

<script>
import MapSelector from '../MapSelector.vue'

export default {
  name: 'LocationSection',

  components: {
    MapSelector
  },

  props: {
    latitude: {
      type: Number,
      default: null
    },
    longitude: {
      type: Number,
      default: null
    },
    scale: {
      type: Number,
      required: true
    },
    sizeCm: {
      type: Number,
      required: true
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },

  emits: ['update:latitude', 'update:longitude'],

  computed: {
    internalLat: {
      get() {
        return this.latitude
      },
      set(value) {
        this.$emit('update:latitude', value)
      }
    },
    internalLng: {
      get() {
        return this.longitude
      },
      set(value) {
        this.$emit('update:longitude', value)
      }
    }
  }
}
</script>
