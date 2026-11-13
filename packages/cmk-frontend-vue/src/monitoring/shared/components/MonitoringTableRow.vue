<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
export type RowVariant = 'error'

withDefaults(
  defineProps<{
    variant?: RowVariant | null | undefined
    hoverable?: boolean | undefined
  }>(),
  { variant: null, hoverable: true }
)
</script>

<template>
  <tr
    class="monitoring-table-row"
    :class="{
      'monitoring-table-row--hoverable': hoverable && variant !== 'error',
      'monitoring-table-row--error': variant === 'error'
    }"
  >
    <slot />
  </tr>
</template>

<style scoped>
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table-row--hoverable:hover :deep(td) {
  background-color: var(--background-row-hover-highlight);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table-row--error :deep(td) {
  background-color: var(--status-background-error);
}
</style>
