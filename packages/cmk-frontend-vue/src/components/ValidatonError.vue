<script setup lang="ts">
const props = defineProps<{
  error: string | null
}>()
</script>

<template>
  <label style="background: #dc5e5e" v-if="error">
    {{ error }}
  </label>
</template>
