<script setup lang="ts">
defineProps<{
  validation: { messages: Array<string> }
}>()
</script>

<template>
  <div v-if="validation.messages" class="validation">
    <ul>
      <li v-for="message in validation.messages" :key="message">&uarr; {{ message }}</li>
    </ul>
  </div>
</template>
