<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject, ref, useSlots } from 'vue'

import {
  type BreakpointValue,
  type CellBreakpoints,
  MONITORING_TABLE_WIDTH,
  resolveBreakpoint
} from '../MonitoringTableContext'

export interface CellLink {
  href: string
  target: '_self' | '_blank' | string | undefined
}

const props = defineProps<{
  breakpoints?: CellBreakpoints | undefined
  hideBelow?: BreakpointValue | undefined
  linkedTo?: CellLink | undefined
}>()

const slots = useSlots()
const containerWidth = inject(MONITORING_TABLE_WIDTH, ref<number>(Number.POSITIVE_INFINITY))

const visible = computed(() => {
  if (props.hideBelow === undefined) {
    return true
  }
  return containerWidth.value >= resolveBreakpoint(props.hideBelow)
})

const activeSlot = computed<string>(() => {
  if (props.breakpoints) {
    const ranked = Object.entries(props.breakpoints)
      .map(([name, value]) => [name, resolveBreakpoint(value)] as const)
      .sort((a, b) => b[1] - a[1])
    for (const [name, threshold] of ranked) {
      if (containerWidth.value >= threshold && slots[name]) {
        return name
      }
    }
  }
  return 'default'
})
</script>

<template>
  <td v-if="visible" class="monitoring-base-cell">
    <a v-if="linkedTo" :href="linkedTo.href" :target="linkedTo.target">
      <slot :name="activeSlot" />
    </a>
    <slot v-else :name="activeSlot" />
  </td>
</template>

<style scoped>
.monitoring-base-cell {
  padding: var(--dimension-2);
}
</style>
