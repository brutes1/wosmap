<template>
  <div class="bg-surface-1 rounded-2xl border border-white/[0.06] p-4 sm:p-6">
    <h2 class="text-lg font-display font-bold text-white mb-4">Print Settings</h2>

    <div class="flex flex-wrap gap-4 items-start">
      <!-- Scale -->
      <div class="flex-1 min-w-[140px]">
        <label class="block text-sm font-medium text-white/50 mb-2">Map Scale</label>
        <select
          :value="scale"
          @change="$emit('update:scale', Number($event.target.value))"
          :disabled="disabled"
          class="w-full px-4 py-3 bg-surface-2 border border-white/[0.08] text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
      <div class="flex-1 min-w-[140px]">
        <label class="block text-sm font-medium text-white/50 mb-2">
          Print Size: <span class="font-semibold text-primary-400">{{ sizeCm }}cm</span>
        </label>
        <input
          type="number"
          :value="sizeCm"
          @input="onSizeInput"
          @change="onSizeChange"
          min="5"
          max="25.6"
          step="0.1"
          :disabled="disabled"
          class="w-full px-4 py-3 bg-surface-2 border border-white/[0.08] text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <p v-if="sizeClamped" class="text-xs text-warning-500 mt-1.5">
          Adjusted to max print size (25.6 cm / 256mm)
        </p>
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
    disabled: {
      type: Boolean,
      default: false
    }
  },

  emits: ['update:scale', 'update:sizeCm'],

  data() {
    return {
      sizeClamped: false
    }
  },

  methods: {
    onSizeInput(event) {
      const val = Number(event.target.value)
      this.sizeClamped = !isNaN(val) && val > 25.6
    },
    onSizeChange(event) {
      let val = Number(event.target.value)
      if (isNaN(val) || val < 5) val = 5
      if (val > 25.6) {
        val = 25.6
        this.sizeClamped = true
        event.target.value = val
      } else {
        this.sizeClamped = false
      }
      this.$emit('update:sizeCm', val)
    }
  }
}
</script>
