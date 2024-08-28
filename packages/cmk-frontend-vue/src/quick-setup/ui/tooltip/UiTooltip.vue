<script setup lang="ts">
import {
  TooltipRoot,
  type TooltipRootEmits,
  type TooltipRootProps,
  useForwardPropsEmits
} from 'radix-vue'

const props = defineProps<TooltipRootProps>()
const emits = defineEmits<TooltipRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <TooltipRoot v-bind="forwarded">
    <slot />
  </TooltipRoot>
</template>
