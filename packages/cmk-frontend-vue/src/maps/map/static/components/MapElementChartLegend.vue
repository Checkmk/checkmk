<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Which curve is which, on a graph object that draws more than one.

Deliberately not Checkmk's full graph legend: a graph on a map is a few hundred
pixels wide, with no room for the per-metric statistics table that legend
carries. Colours come from the same resolution the curves do, so the two cannot
drift apart.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

export interface LegendEntry {
  key: string
  label: string
  color: string
  /** Latest reading, formatted as Checkmk formats it. */
  value: string
}

/** Curves a card this size can label before the legend crowds out the graph. */
const MAX_VISIBLE = 6

const { _t } = usei18n()

const props = defineProps<{ entries: LegendEntry[] }>()

const visible = computed(() => props.entries.slice(0, MAX_VISIBLE))
const hidden = computed(() => props.entries.slice(MAX_VISIBLE))
const hiddenLabels = computed(() => hidden.value.map((entry) => entry.label).join(', '))
</script>

<template>
  <div class="maps-map-element-chart-legend">
    <div v-for="entry in visible" :key="entry.key" class="maps-map-element-chart-legend__item">
      <span class="maps-map-element-chart-legend__swatch" :style="{ background: entry.color }" />
      <span class="maps-map-element-chart-legend__label">{{ entry.label }}</span>
      <span class="maps-map-element-chart-legend__value" :style="{ color: entry.color }">{{
        entry.value
      }}</span>
    </div>
    <span
      v-if="hidden.length > 0"
      class="maps-map-element-chart-legend__more"
      :title="hiddenLabels"
      >{{ _t('+%{n}', { n: hidden.length }) }}</span
    >
  </div>
</template>

<style scoped>
.maps-map-element-chart-legend {
  display: flex;
  flex-wrap: wrap;
  flex-shrink: 0;
  gap: var(--dimension-2) 10px;
  margin-bottom: var(--dimension-3);
}

.maps-map-element-chart-legend__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  min-width: 0;
  max-width: 50%;
}

.maps-map-element-chart-legend__swatch {
  display: inline-block;
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.maps-map-element-chart-legend__label {
  overflow: hidden;
  font-size: 9px;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-map-element-chart-legend__value {
  flex-shrink: 0;
  font-size: 9px;
  font-weight: var(--font-weight-bold);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.maps-map-element-chart-legend__more {
  align-self: center;
  font-size: 9px;
  color: var(--font-color-dimmed);
  cursor: default;
}
</style>
