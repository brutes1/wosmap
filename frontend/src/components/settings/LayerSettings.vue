<template>
  <div class="bg-white rounded-2xl shadow-lg shadow-slate-900/5 border border-slate-100 p-4 sm:p-6">
    <h2 class="text-xl font-bold text-slate-900 mb-4">Map Layers</h2>
    <p class="text-sm text-slate-500 mb-4">Select which features to include in your tactile map.</p>

    <div class="space-y-1">
      <label
        v-for="layer in layerConfig"
        :key="layer.id"
        class="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all hover:bg-slate-50"
        :class="{ 'opacity-50 cursor-not-allowed': disabled }"
      >
        <input
          type="checkbox"
          :checked="modelValue[layer.id]"
          @change="toggleLayer(layer.id, $event.target.checked)"
          :disabled="disabled"
          class="w-5 h-5 rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50"
        />
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-800">{{ layer.name }}</span>
            <span
              v-if="layer.beta"
              class="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium"
            >
              Beta
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">{{ layer.description }}</p>
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
    description: 'Hills, valleys, topography',
    beta: true,
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
