<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One metric as a bar, with its warning and critical levels marked on it.

Where a value sits between its levels is the thing an operator reads first, so
the levels are drawn on the bar rather than stated next to it. The headline
metric gets the same bar, only taller.
-->
<script setup lang="ts">
defineProps<{
  /** How far the bar is filled, 0..100. */
  pct: number
  /** The bar's own colour, resolved by the caller from the metric registry. */
  color: string
  warnPct?: number | null | undefined
  critPct?: number | null | undefined
  warnLabel?: string | undefined
  critLabel?: string | undefined
  /** The headline metric's bar, drawn taller than a raw metric's. */
  large?: boolean
}>()
</script>

<template>
  <div class="maps-detail-perf-bar" :class="large ? 'maps-detail-perf-bar--large' : ''">
    <div
      class="maps-detail-perf-bar__fill"
      :style="{ width: `${pct}%`, background: color }"
      role="presentation"
    />
    <div
      v-if="warnPct !== null && warnPct !== undefined"
      class="maps-detail-perf-bar__mark maps-detail-perf-bar__mark--warn"
      :style="{ left: `${warnPct}%` }"
      :title="`warn: ${warnLabel}`"
    />
    <div
      v-if="critPct !== null && critPct !== undefined"
      class="maps-detail-perf-bar__mark maps-detail-perf-bar__mark--crit"
      :style="{ left: `${critPct}%` }"
      :title="`crit: ${critLabel}`"
    />
  </div>
</template>

<style scoped>
.maps-detail-perf-bar {
  position: relative;
  height: 8px;
  background: var(--ux-theme-1);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.maps-detail-perf-bar--large {
  height: 14px;
  border-radius: 6px;
}

.maps-detail-perf-bar__fill {
  height: 100%;
  transition: width 0.2s ease;
}

.maps-detail-perf-bar__mark {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
}

.maps-detail-perf-bar__mark--warn {
  background: color-mix(in srgb, var(--color-state-warning) 80%, transparent);
}

.maps-detail-perf-bar__mark--crit {
  background: color-mix(in srgb, var(--color-state-critical) 80%, transparent);
}
</style>
