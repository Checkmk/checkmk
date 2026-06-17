<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Stacking axis: `column` (default) stacks children vertically, `row` lays them side by side. */
    direction?: 'row' | 'column'
  }>(),
  {
    direction: 'column'
  }
)

defineSlots<{
  /** The stacked content (children, and any HorizontalRule/VerticalRule between them). */
  default?: () => unknown
}>()
</script>

<template>
  <div class="cmk-stack-layout" :class="`cmk-stack-layout--${direction}`">
    <slot />
  </div>
</template>

<style scoped>
/* Owns both the inset padding and the spacing between children (and any HorizontalRule/
   VerticalRule between them), so spacing stays consistent within and across the pickers. */
.cmk-stack-layout {
  display: flex;
  gap: var(--dimension-7);
  padding: var(--dimension-7);
  align-items: center;
}

.cmk-stack-layout--column {
  flex-direction: column;
}

.cmk-stack-layout--row {
  flex-direction: row;
}
</style>
