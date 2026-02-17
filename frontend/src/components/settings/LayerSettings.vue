<template>
  <div class="bg-surface-1 rounded-2xl border border-white/[0.06] p-4 sm:p-6">
    <h2 class="text-lg font-display font-bold text-white mb-2">Map Layers</h2>
    <p class="text-sm text-white/40 mb-4">Select features to include.</p>

    <div class="space-y-0.5">
      <label
        v-for="layer in layerConfig"
        :key="layer.id"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all"
        :class="{
          'opacity-40 cursor-not-allowed': disabled || layer.comingSoon,
          'cursor-pointer hover:bg-surface-2': !disabled && !layer.comingSoon
        }"
      >
        <input
          type="checkbox"
          :checked="modelValue[layer.id]"
          @change="toggleLayer(layer.id, $event.target.checked)"
          :disabled="disabled || layer.comingSoon"
          class="w-4 h-4 rounded border-white/20 bg-surface-2 text-primary-500 focus:ring-primary-500 focus:ring-offset-0 disabled:opacity-50"
        />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium" :class="layer.comingSoon ? 'text-white/30' : 'text-white/80'">{{ layer.name }}</span>
            <span
              v-if="layer.comingSoon"
              class="text-[10px] bg-white/[0.06] text-white/30 px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wider"
            >
              Soon
            </span>
          </div>
          <p class="text-xs text-white/30 mt-0.5">{{ layer.description }}</p>
        </div>
      </label>
    </div>
  </div>
</template>

<script>
const LAYER_CONFIG = [
  {
    id: 'buildings',
    name: 'Buildings',
    description: 'Building footprints and heights',
  },
  {
    id: 'roads',
    name: 'Roads & Streets',
    description: 'Streets, highways, sidewalks',
  },
  {
    id: 'water',
    name: 'Water Bodies',
    description: 'Lakes, ponds, reservoirs',
  },
  {
    id: 'rivers',
    name: 'Rivers & Streams',
    description: 'Flowing waterways and canals',
  },
  {
    id: 'parks',
    name: 'Parks & Green Spaces',
    description: 'Recreation areas, forests',
  },
  {
    id: 'trails',
    name: 'Trails & Footpaths',
    description: 'Hiking trails, walking paths',
  },
  {
    id: 'terrain',
    name: 'Terrain/Elevation',
    description: 'Coming soon - requires elevation data integration',
    comingSoon: true,
  },
]

export default {
  name: 'LayerSettings',

  props: {
    modelValue: {
      type: Object,
      required: true,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['update:modelValue'],

  data() {
    return {
      layerConfig: LAYER_CONFIG,
    }
  },

  methods: {
    toggleLayer(layerId, checked) {
      this.$emit('update:modelValue', {
        ...this.modelValue,
        [layerId]: checked,
      })
    },
  },
}
</script>
