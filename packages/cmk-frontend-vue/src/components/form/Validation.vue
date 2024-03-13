<script setup lang="ts">
const props = defineProps<{
  validation: any
}>()
</script>

<template>
  <div v-if="validation.messages" class="validation">
    <ul>
      <li v-for="message in validation.messages">&uarr; {{ message }}</li>
    </ul>
  </div>
</template>
