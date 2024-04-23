<script setup lang="ts">
defineProps<{
  error: string | null
}>()
</script>

<template>
  <label v-if="error" style="background: #dc5e5e">
    {{ error }}
  </label>
</template>
