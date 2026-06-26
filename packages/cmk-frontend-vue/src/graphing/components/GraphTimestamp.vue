<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { TimeRange } from './TimeSeriesGraph'

const props = defineProps<{ timeRange: TimeRange }>()

function isoDate(unix: number): string {
  const d = new Date(unix * 1000)
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  return `${y}-${mo}-${da}`
}

function shortWeekday(unix: number): string {
  return new Date(unix * 1000).toLocaleDateString(undefined, { weekday: 'short' })
}

// Mirrors the backend's get_step_label()
function stepLabel(step: number): string {
  const fmt = (n: number) => (n % 1 === 0 ? String(n) : n.toFixed(1))
  if (step < 3600) {
    return `${fmt(step / 60)} m`
  }
  if (step < 86400) {
    return `${fmt(step / 3600)} h`
  }
  return `${fmt(step / 86400)} d`
}

const label = computed(() => {
  const { start, end, step } = props.timeRange
  const startDate = isoDate(start)
  const endDate = isoDate(end)
  const stepStr = `@ ${stepLabel(step)}`
  if (startDate === endDate) {
    return `${shortWeekday(start)}, ${startDate} ${stepStr}`
  }
  return `${startDate} — ${endDate} ${stepStr}`
})
</script>

<template>
  <div class="graphing-graph-timestamp">{{ label }}</div>
</template>

<style scoped lang="scss">
.graphing-graph-timestamp {
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
}
</style>
