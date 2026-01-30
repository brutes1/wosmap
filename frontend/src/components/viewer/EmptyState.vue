<template>
  <div class="absolute inset-0 flex items-center justify-center bg-slate-50">
    <div class="text-center p-8">
      <!-- 3D Cube Icon -->
      <div class="w-20 h-20 mx-auto mb-6 text-slate-300">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
        </svg>
      </div>
      <h3 class="text-xl font-semibold text-slate-700 mb-2">No 3D Preview Yet</h3>
      <p class="text-slate-500 max-w-xs mx-auto">
        Select a location and generate a map to see an interactive 3D preview here
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EmptyState'
}
</script>
