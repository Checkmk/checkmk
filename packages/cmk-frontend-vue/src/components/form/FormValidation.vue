<script setup lang="ts">
defineProps<{
  validation: any
}>()
</script>

<template>
  <div v-if="validation.messages" class="validation">
    <ul>
      <li v-for="message in validation.messages" :key="message">&uarr; {{ message }}</li>
    </ul>
  </div>
</template>
