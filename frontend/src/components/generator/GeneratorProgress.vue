<template>
  <div class="bg-surface-1 rounded-2xl border border-white/[0.06] p-6">
    <h3 class="text-lg font-display font-bold text-white mb-4">Generating Map...</h3>

    <div class="flex flex-wrap gap-2">
      <span
        v-for="(stage, index) in stages"
        :key="stage.id"
        class="px-3 py-1.5 rounded-full text-sm font-medium transition-all"
        :class="getStageClass(stage.id)"
      >
        {{ stage.label }}
      </span>
    </div>

    <p v-if="stageMessage" class="mt-4 text-sm text-white/60">
      {{ stageMessage }}
    </p>

    <p v-if="error" class="mt-4 text-sm text-danger-500 font-medium">
      {{ error }}
    </p>
  </div>
</template>

<script>
export default {
  name: 'GeneratorProgress',

  props: {
    stages: {
      type: Array,
      required: true
    },
    currentStage: {
      type: String,
      default: null
    },
    stageMessage: {
      type: String,
      default: ''
    },
    error: {
      type: String,
      default: null
    }
  },

  methods: {
    getStageClass(stageId) {
      const stageOrder = this.stages.map(s => s.id)
      const currentIndex = stageOrder.indexOf(this.currentStage)
      const stageIndex = stageOrder.indexOf(stageId)

      if (stageIndex < currentIndex) {
        return 'bg-success-500 text-white'
      } else if (stageIndex === currentIndex) {
        return 'bg-primary-500 text-navy-950 animate-pulse'
      } else {
        return 'bg-surface-2 text-white/30'
      }
    }
  }
}
</script>
