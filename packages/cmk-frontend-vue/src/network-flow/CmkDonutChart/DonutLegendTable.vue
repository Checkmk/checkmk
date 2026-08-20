<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import GraphLegendEyeButton from '@/graphing/components/legend/GraphLegendEyeButton.vue'

import { chartColorCss } from '../colors'
import type { DonutLegendRow } from './types'

const { _t } = usei18n()

defineProps<{
  rows: DonutLegendRow[]
  highlighted: string | null
}>()

defineEmits<{
  toggle: [key: string]
  highlight: [key: string | null]
}>()
</script>

<template>
  <ul class="network-flow-donut-legend-table">
    <li
      v-for="row in rows"
      :key="row.key"
      class="network-flow-donut-legend-table__row"
      :class="{
        'network-flow-donut-legend-table__row--highlighted': highlighted === row.key,
        'network-flow-donut-legend-table__row--hidden': row.hidden
      }"
      @mouseenter="$emit('highlight', row.key)"
      @mouseleave="$emit('highlight', null)"
    >
      <GraphLegendEyeButton
        :hidden="row.hidden"
        :aria-label="
          row.hidden
            ? _t('Show %{category} in the chart', { category: row.label })
            : _t('Hide %{category} in the chart', { category: row.label })
        "
        @toggle="$emit('toggle', row.key)"
      />
      <span
        class="network-flow-donut-legend-table__swatch"
        :style="{ backgroundColor: row.hidden ? '' : chartColorCss(row.color) }"
      />
      <span class="network-flow-donut-legend-table__label">{{ row.label }}</span>
      <span class="network-flow-donut-legend-table__value">{{ row.shareText }}</span>
    </li>
  </ul>
</template>

<style scoped>
.network-flow-donut-legend-table {
  flex: 1;
  min-width: 0;
  padding: 0;
  margin: 0;
  overflow: hidden;
  list-style: none;
}

.network-flow-donut-legend-table__row {
  display: flex;
  gap: clamp(4px, 1cqw, 10px);
  align-items: center;
  padding: clamp(2px, 1.5cqh, 7px) 0;
  border-bottom: 1px solid var(--ux-theme-6);
}

.network-flow-donut-legend-table__row--highlighted {
  background-color: var(--ux-theme-4);
}

/* A hidden category keeps its row, so it stays reachable. */
.network-flow-donut-legend-table__row--hidden {
  opacity: 0.45;
}

.network-flow-donut-legend-table__swatch {
  flex: 0 0 auto;
  width: 0.75em;
  height: 0.75em;
  border-radius: 2px;
}

.network-flow-donut-legend-table__row--hidden .network-flow-donut-legend-table__swatch {
  background-color: var(--color-mid-grey-30);
}

.network-flow-donut-legend-table__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.network-flow-donut-legend-table__value {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
