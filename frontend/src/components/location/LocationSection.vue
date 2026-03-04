<template>
  <MapSelector
    v-model:latitude="internalLat"
    v-model:longitude="internalLng"
    :scale="scale"
    :size-cm="sizeCm"
    :disabled="disabled"
  />
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
