<script setup lang="ts">
import { CollapsibleContent, type CollapsibleContentProps } from 'radix-vue'

const props = defineProps<CollapsibleContentProps>()
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <CollapsibleContent v-bind="props" class="ui-collapsible-content">
    <slot />
  </CollapsibleContent>
</template>

<style scoped>
.ui-collapsible-content {
  overflow: hidden;

  &[data-state='open'] {
    animation: slideDown 300ms ease-out;
  }

  &[data-state='closed'] {
    animation: slideUp 300ms ease-out;
  }
}

@keyframes slideDown {
  from {
    height: 0;
  }
  to {
    height: var(--radix-collapsible-content-height);
  }
}

@keyframes slideUp {
  from {
    height: var(--radix-collapsible-content-height);
  }
  to {
    height: 0;
  }
}
</style>
