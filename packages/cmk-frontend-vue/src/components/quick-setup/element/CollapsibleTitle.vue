<script setup lang="ts">
import InlineChevron from './InlineChevron.vue'

interface CollapsibleTitleProps {
  label: string
  open: boolean
}

defineProps<CollapsibleTitleProps>()
defineEmits(['toggleOpen'])
</script>

<template>
  <button class="text-button" @click="$emit('toggleOpen')">
    <InlineChevron :variant="open ? 'bottom' : 'right'" />
    <span class="collapsible-title-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.text-button {
  position: relative;
  left: -27px;
  background: none;
  border: none;
  cursor: pointer;
}
.text-button:hover {
  background-color: none;
}

.collapsible-title-label {
  color: #13d389;
  font-weight: bold;
  padding-left: 5px;
}
</style>
