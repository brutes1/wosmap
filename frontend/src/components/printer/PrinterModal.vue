<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click.self="$emit('close')"
    >
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 sm:p-8">
        <h3 class="text-xl font-bold text-slate-900 mb-2">Configure Bambu X1C Printer</h3>
        <p class="text-sm text-slate-500 mb-6">
          Developer Mode must be enabled on your printer.
          <a
            href="https://wiki.bambulab.com/en/knowledge-sharing/enable-developer-mode"
            target="_blank"
            class="text-primary-600 hover:text-primary-700 underline"
          >
            Learn more
          </a>
        </p>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Printer IP Address</label>
            <input
              v-model="printerIp"
              type="text"
              placeholder="192.168.1.100"
              class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Access Code (8 digits)</label>
            <input
              v-model="printerAccessCode"
              type="text"
              placeholder="12345678"
              maxlength="8"
              class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-2">Serial Number</label>
            <input
              v-model="printerSerial"
              type="text"
              placeholder="00M00A000000000"
              class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all"
            />
          </div>
        </div>

        <div class="flex gap-3 mt-8">
          <button
            @click="$emit('close')"
            class="flex-1 px-5 py-3 bg-white hover:bg-slate-50 text-slate-700 font-semibold border border-slate-200 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            @click="handleSubmit"
            :disabled="!isValid"
            class="flex-1 px-5 py-3 bg-primary-600 hover:bg-primary-700 text-white font-semibold rounded-xl shadow-lg shadow-primary-600/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
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
