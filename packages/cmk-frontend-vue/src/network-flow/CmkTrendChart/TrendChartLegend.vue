<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import { chartColorCss } from '../colors'
import type { TrendChartSeriesWithColor } from './types'

const { _t } = usei18n()

defineProps<{
  series: TrendChartSeriesWithColor[]
  formatValue: (value: number) => string
  /** When true, each series name renders as a button emitting `nameClick`. */
  clickable?: boolean
}>()

const emit = defineEmits<{ nameClick: [name: string] }>()
</script>

<template>
  <table class="network-flow-trend-chart-legend">
    <thead>
      <tr>
        <th class="network-flow-trend-chart-legend__th network-flow-trend-chart-legend__th--name">
          &nbsp;
        </th>
        <th class="network-flow-trend-chart-legend__th network-flow-trend-chart-legend__th--value">
          {{ _t('Minimum') }}
        </th>
        <th class="network-flow-trend-chart-legend__th network-flow-trend-chart-legend__th--value">
          {{ _t('Maximum') }}
        </th>
        <th class="network-flow-trend-chart-legend__th network-flow-trend-chart-legend__th--value">
          {{ _t('Average') }}
        </th>
        <th class="network-flow-trend-chart-legend__th network-flow-trend-chart-legend__th--value">
          {{ _t('Last') }}
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(item, index) in series" :key="index" class="network-flow-trend-chart-legend__row">
        <td class="network-flow-trend-chart-legend__td network-flow-trend-chart-legend__td--name">
          <span
            class="network-flow-trend-chart-legend__swatch"
            :style="{ backgroundColor: chartColorCss(item.color) }"
          />
          <button
            v-if="clickable"
            type="button"
            class="network-flow-trend-chart-legend__name network-flow-trend-chart-legend__name--link"
            @click="emit('nameClick', item.name)"
          >
            {{ item.name }}
          </button>
          <span v-else class="network-flow-trend-chart-legend__name">{{ item.name }}</span>
        </td>
        <td class="network-flow-trend-chart-legend__td network-flow-trend-chart-legend__td--value">
          {{ formatValue(item.minimum) }}
        </td>
        <td class="network-flow-trend-chart-legend__td network-flow-trend-chart-legend__td--value">
          {{ formatValue(item.maximum) }}
        </td>
        <td class="network-flow-trend-chart-legend__td network-flow-trend-chart-legend__td--value">
          {{ formatValue(item.average) }}
        </td>
        <td
          class="network-flow-trend-chart-legend__td network-flow-trend-chart-legend__td--value network-flow-trend-chart-legend__td--last"
        >
          {{ formatValue(item.last) }}
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
.network-flow-trend-chart-legend {
  width: 100%;
  border-collapse: collapse;
  font-size: clamp(11px, 9cqh, 14px);
}

.network-flow-trend-chart-legend__th {
  padding: clamp(2px, 2cqh, 6px) clamp(6px, 1cqw, 12px);
  font-size: 0.85em;
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
  border-bottom: 1px solid var(--ux-theme-4);
}

.network-flow-trend-chart-legend__th--value {
  text-align: right;
}

.network-flow-trend-chart-legend__td {
  padding: clamp(2px, 2cqh, 6px) clamp(6px, 1cqw, 12px);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.network-flow-trend-chart-legend__td--value {
  font-variant-numeric: tabular-nums;
  text-align: right;
}

/* The "Last" value is the headline of the row, matching the mockups. */
.network-flow-trend-chart-legend__td--last {
  font-weight: var(--font-weight-bold);
}

.network-flow-trend-chart-legend__td--name {
  display: flex;
  gap: clamp(4px, 1cqw, 8px);
  align-items: center;
  width: 100%;
}

.network-flow-trend-chart-legend__swatch {
  flex: none;
  width: 0.75em;
  height: 0.75em;
  border-radius: 2px;
}

.network-flow-trend-chart-legend__name {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Clickable series name: a bare button styled like CmkLink. */
.network-flow-trend-chart-legend__name--link {
  padding: 0;
  font: inherit;
  color: inherit;
  text-decoration: underline;
  cursor: pointer;
  background: none;
  border: none;
}

.network-flow-trend-chart-legend__name--link:hover {
  color: var(--cmk-link-hover-color, #15d1a0);
}
</style>
