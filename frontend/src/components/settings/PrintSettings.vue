<template>
  <div class="bg-white rounded-2xl shadow-lg shadow-slate-900/5 border border-slate-100 p-4 sm:p-6">
    <h2 class="text-xl font-bold text-slate-900 mb-6">Print Settings</h2>

    <div class="space-y-5">
      <!-- Scale and Size row -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Scale -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">Map Scale</label>
          <select
            :value="scale"
            @change="$emit('update:scale', Number($event.target.value))"
            :disabled="disabled"
            class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option :value="1000">1:1,000 (Very detailed)</option>
            <option :value="2000">1:2,000</option>
            <option :value="3463">1:3,463 (Default)</option>
            <option :value="5000">1:5,000</option>
            <option :value="7500">1:7,500</option>
            <option :value="10000">1:10,000 (Wide area)</option>
          </select>
        </div>

        <!-- Print Size -->
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">
            Print Size: <span class="font-bold text-primary-600">{{ sizeCm }}cm</span>
          </label>
          <input
            type="number"
            :value="sizeCm"
            @input="$emit('update:sizeCm', Number($event.target.value))"
            min="5"
            max="50"
            step="1"
            :disabled="disabled"
            class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      <!-- Buildings toggle -->
      <label class="flex items-center gap-3 cursor-pointer">
        <input
          type="checkbox"
          :checked="includeBuildings"
          @change="$emit('update:includeBuildings', $event.target.checked)"
          :disabled="disabled"
          class="w-5 h-5 rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50"
        />
        <span class="text-slate-700">Include 3D buildings</span>
      </label>

      <!-- Data Source -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-3">Data Source</label>
        <div class="grid grid-cols-2 gap-3">
          <label
            class="flex flex-col items-center justify-center gap-1 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
            :class="[
              dataSource === 'osm'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-slate-200 hover:border-slate-300',
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            ]"
          >
            <input
              type="radio"
              value="osm"
              :checked="dataSource === 'osm'"
              @change="$emit('update:dataSource', 'osm')"
              :disabled="disabled"
              class="sr-only"
            />
            <span class="font-semibold">OpenStreetMap</span>
            <span class="text-xs text-slate-500">Community-sourced</span>
          </label>
          <label
            class="flex flex-col items-center justify-center gap-1 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all"
            :class="[
              dataSource === 'overture'
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-slate-200 hover:border-slate-300',
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            ]"
          >
            <input
              type="radio"
              value="overture"
              :checked="dataSource === 'overture'"
              @change="$emit('update:dataSource', 'overture')"
              :disabled="disabled"
              class="sr-only"
            />
            <span class="font-semibold">Overture Maps</span>
            <span class="text-xs text-slate-500">OSM + Microsoft + Google</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PrintSettings',

  props: {
    scale: {
      type: Number,
      required: true
    },
    sizeCm: {
      type: Number,
      required: true
    },
    includeBuildings: {
      type: Boolean,
      required: true
    },
    dataSource: {
      type: String,
      required: true
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },

  emits: ['update:scale', 'update:sizeCm', 'update:includeBuildings', 'update:dataSource']
}
</script>
