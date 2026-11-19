<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useDeferredPlainClick } from '@/monitoring/shared/plainClick'

export type RowVariant = 'error'

const props = withDefaults(
  defineProps<{
    variant?: RowVariant | null | undefined
    hoverable?: boolean | undefined
    /** Opens the row's details on a click anywhere in it. */
    clickable?: boolean | undefined
  }>(),
  { variant: null, hoverable: true, clickable: false }
)

const emit = defineEmits<{
  (event: 'open'): void
}>()

const open = useDeferredPlainClick(() => emit('open'))

function onClick(event: MouseEvent): void {
  if (props.clickable) {
    open(event)
  }
}
</script>

<template>
  <tr
    class="monitoring-table-row"
    :class="{
      'monitoring-table-row--hoverable': hoverable && variant !== 'error',
      'monitoring-table-row--error': variant === 'error',
      'monitoring-table-row--clickable': clickable
    }"
    @click="onClick"
  >
    <slot />
  </tr>
</template>

<style scoped>
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table-row--hoverable:hover :deep(td) {
  background-color: var(--background-row-hover-highlight);
}

.monitoring-table-row--clickable {
  cursor: pointer;
}

/* Read by the row's main cell, which shows its open-details icon then. */
.monitoring-table-row--clickable:hover {
  --monitoring-table-row-main-icon-visibility: visible;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.monitoring-table-row--error :deep(td) {
  background-color: var(--status-background-error);
}
</style>
