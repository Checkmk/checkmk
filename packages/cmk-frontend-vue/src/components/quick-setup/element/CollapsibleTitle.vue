<script setup lang="ts">
import InlineChevron from './InlineChevron.vue'

interface CollapsibleTitleProps {
  /**@property {string} title - Text to display next to the chevron */
  title: string

  /** @property {boolean} open - If true, the collapsible element will be open by default,
   * otherwise it will be rendered closed
   */
  open: boolean
}

defineProps<CollapsibleTitleProps>()
defineEmits(['toggleOpen'])
</script>

<template>
  <button class="text-button" @click="$emit('toggleOpen')">
    <InlineChevron :variant="open ? 'bottom' : 'right'" />
    <span class="collapsible-title">{{ title }}</span>
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

.collapsible-title {
  color: #13d389;
  font-weight: bold;
  padding-left: 5px;
}
</style>
