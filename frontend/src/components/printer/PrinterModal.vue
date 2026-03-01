<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="$emit('close')"
    >
      <div class="bg-surface-1 rounded-2xl shadow-2xl border border-white/[0.08] max-w-md w-full p-6 sm:p-8">
        <h3 class="text-xl font-display font-bold text-white mb-2">Configure Bambu X1C Printer</h3>
        <p class="text-sm text-white/40 mb-6">
          Developer Mode must be enabled on your printer.
          <a
            href="https://wiki.bambulab.com/en/knowledge-sharing/enable-developer-mode"
            target="_blank"
            class="text-primary-400 hover:text-primary-500 underline"
          >
            Learn more
          </a>
        </p>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-white/50 mb-2">Printer IP Address</label>
            <input
              v-model="printerIp"
              type="text"
              placeholder="192.168.1.100"
              class="w-full px-4 py-3 bg-surface-2 border border-white/[0.08] text-white rounded-xl placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-white/50 mb-2">Access Code (8 digits)</label>
            <input
              v-model="printerAccessCode"
              type="text"
              placeholder="12345678"
              maxlength="8"
              class="w-full px-4 py-3 bg-surface-2 border border-white/[0.08] text-white rounded-xl placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-white/50 mb-2">Serial Number</label>
            <input
              v-model="printerSerial"
              type="text"
              placeholder="00M00A000000000"
              class="w-full px-4 py-3 bg-surface-2 border border-white/[0.08] text-white rounded-xl placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        <div class="flex gap-3 mt-8">
          <button
            @click="$emit('close')"
            class="flex-1 px-5 py-3 bg-surface-2 hover:bg-surface-3 text-white font-semibold border border-white/[0.08] rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleSubmit"
            :disabled="!isValid"
            class="flex-1 px-5 py-3 bg-primary-500 hover:bg-primary-400 text-navy-950 font-semibold rounded-xl shadow-lg shadow-primary-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
          >
            Save & Print
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
export default {
  name: 'PrinterModal',

  props: {
    show: {
      type: Boolean,
      default: false
    }
  },

  emits: ['close', 'submit'],

  data() {
    return {
      printerIp: '',
      printerAccessCode: '',
      printerSerial: ''
    }
  },

  computed: {
    isValid() {
      return this.printerIp.trim() && this.printerAccessCode.trim() && this.printerSerial.trim()
    }
  },

  methods: {
    handleSubmit() {
      if (!this.isValid) return

      this.$emit('submit', {
        ip: this.printerIp,
        access_code: this.printerAccessCode,
        serial: this.printerSerial
      })
    }
  }
}
</script>
