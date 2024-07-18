<script setup lang="ts">
import { CollapsibleRoot, useForwardPropsEmits } from 'radix-vue'
import type { CollapsibleRootEmits, CollapsibleRootProps } from 'radix-vue'

const props = defineProps<CollapsibleRootProps>()
const emits = defineEmits<CollapsibleRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <CollapsibleRoot v-slot="{ open: openSlot }" v-bind="forwarded" class="ui-collapsible">
    <slot :open="openSlot" />
  </CollapsibleRoot>
</template>

<style scoped>
.ui-collapsible {
  padding-top: 1rem;
}
</style>
