<script setup lang="ts">
import { TooltipTrigger, type TooltipTriggerProps } from 'radix-vue'

const props = defineProps<TooltipTriggerProps>()
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <TooltipTrigger v-bind="props">
    <slot />
  </TooltipTrigger>
</template>
