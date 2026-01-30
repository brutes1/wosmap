<template>
  <div class="bg-gradient-to-br from-slate-50 to-white rounded-2xl border border-slate-200 p-6 mt-6">
    <h3 class="text-lg font-bold text-slate-900 mb-4">Generating Map...</h3>

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

    <p v-if="stageMessage" class="mt-4 text-sm text-slate-600">
      {{ stageMessage }}
    </p>

    <p v-if="error" class="mt-4 text-sm text-danger-600 font-medium">
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
        return 'bg-primary-500 text-white animate-pulse'
      } else {
        return 'bg-slate-200 text-slate-500'
      }
    }
  }
}
</script>
