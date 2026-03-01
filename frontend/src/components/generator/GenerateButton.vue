<template>
  <button
    @click="$emit('click')"
    :disabled="disabled || loading"
    class="w-full px-6 py-4 bg-primary-500 hover:bg-primary-400 text-navy-950 text-lg font-bold rounded-xl shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-400/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none disabled:hover:bg-primary-500"
  >
    <span v-if="loading" class="flex items-center justify-center gap-2">
      <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Generating...
    </span>
    <span v-else>Generate Map</span>
  </button>
</template>

<script>
export default {
  name: 'GenerateButton',

  props: {
    disabled: {
      type: Boolean,
      default: false
    },
    loading: {
      type: Boolean,
      default: false
    }
  },

  emits: ['click']
}
</script>
