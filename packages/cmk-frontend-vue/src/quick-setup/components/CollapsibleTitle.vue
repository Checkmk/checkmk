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
  <button class="qs-collapsible-title" @click="$emit('toggleOpen')">
    <InlineChevron :variant="open ? 'bottom' : 'right'" />
    <span class="qs-collapsible-title__text">{{ title }}</span>
  </button>
</template>

<style scoped>
.qs-collapsible-title {
  position: relative;
  left: -27px;
  background: none;
  border: none;
  cursor: pointer;

  &:hover {
    background-color: none;
  }
}

.qs-collapsible-title__text {
  color: var(--success-dimmed);
  font-weight: var(--font-weight-bold);
}
</style>
