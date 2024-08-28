<script setup lang="ts">
import { TooltipProvider, type TooltipProviderProps } from 'radix-vue'

const props = defineProps<TooltipProviderProps>()
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <TooltipProvider v-bind="props">
    <slot />
  </TooltipProvider>
</template>
