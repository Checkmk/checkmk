<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The numbers behind the state.

The one metric the check's own Perf-O-Meter puts first gets the headline and a
graph of the last minutes; the plugin's own breakdown text comes next, because
whoever wrote the check already said what matters; and everything else is a
list the operator can open if they want it.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import MetricChart from '@/maps/map/components/MetricChart'
import type { MetricPoint } from '@/maps/types/api'

import type { LongOutputRow, MainHeadline, PerfRow } from '../composables/usePerformanceMetrics'
import DetailPerfBar from './DetailPerfBar.vue'

defineProps<{
  headline: MainHeadline | null
  /** The headline metric's own row, for its warning and critical levels. */
  headlineRow: PerfRow | null
  /** Recent samples of the headline metric, where the site kept any. */
  historyData: Record<string, MetricPoint[]>
  historyKey: string | null
  historyThresholds: { warn: number | null; crit: number | null } | null
  historyWindowSecs: number
  /** The headline metric's raw perfdata unit, for labels the registry misses. */
  headlineUnit: string | undefined
  longOutputRows: LongOutputRow[]
  otherRows: PerfRow[]
}>()

const { _t } = usei18n()
</script>

<template>
  <div class="maps-detail-performance-tab">
    <div v-if="headline" class="maps-detail-performance-tab__headline">
      <span class="maps-detail-performance-tab__headline-label">{{ headline.label }}</span>
      <DetailPerfBar
        large
        :pct="headline.pct"
        :color="headline.color"
        :warn-pct="headlineRow?.warnPct"
        :crit-pct="headlineRow?.critPct"
        :warn-label="headlineRow?.warnLabel"
        :crit-label="headlineRow?.critLabel"
      />
      <div v-if="headline.valueLabel" class="maps-detail-performance-tab__headline-value">
        {{ headline.valueLabel }}
      </div>
    </div>

    <div v-if="historyKey" class="maps-detail-performance-tab__chart">
      <MetricChart
        :data="historyData"
        :metric-keys="[historyKey]"
        :window-secs="historyWindowSecs"
        :thresholds="historyThresholds"
        :unit="headlineUnit"
      />
    </div>

    <div v-if="longOutputRows.length">
      <div class="maps-detail-performance-tab__heading">{{ _t('Details') }}</div>
      <dl class="maps-detail-performance-tab__output-rows">
        <template v-for="(row, index) in longOutputRows" :key="index">
          <dt v-if="row.label">{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </template>
      </dl>
    </div>

    <details v-if="otherRows.length" class="maps-detail-performance-tab__raw">
      <summary>{{ _t('Raw metrics (%{n})', { n: otherRows.length }) }}</summary>
      <div class="maps-detail-performance-tab__rows">
        <div v-for="row in otherRows" :key="row.label" class="maps-detail-performance-tab__row">
          <div class="maps-detail-performance-tab__row-label" :title="row.label">
            {{ row.label }}
          </div>
          <DetailPerfBar
            :pct="row.pct"
            :color="row.color"
            :warn-pct="row.warnPct"
            :crit-pct="row.critPct"
            :warn-label="row.warnLabel"
            :crit-label="row.critLabel"
          />
          <div class="maps-detail-performance-tab__row-value">{{ row.valueLabel }}</div>
        </div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.maps-detail-performance-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: 12px 16px;
}

/* The status-driving value, anchored at the top so it is read without
   scanning. */
.maps-detail-performance-tab__headline {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 0 6px;
}

.maps-detail-performance-tab__headline-label {
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: var(--font-weight-bold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-detail-performance-tab__headline-value {
  color: var(--font-color);
  font-size: var(--font-size-xxlarge);
  font-weight: var(--font-weight-bold);
  font-variant-numeric: tabular-nums;
}

.maps-detail-performance-tab__chart {
  height: 120px;
  margin: 4px 0;
}

.maps-detail-performance-tab__heading {
  font-size: var(--font-size-small);
  text-transform: uppercase;
  color: var(--font-color-dimmed);
  letter-spacing: 0.04em;
  font-weight: var(--font-weight-bold);
  margin: 4px 0 6px;
}

/* The plugin's own breakdown, as a label/value table. Treated as the primary
   reading of the metrics, so the bars below do not repeat it. */
.maps-detail-performance-tab__output-rows {
  display: grid;
  grid-template-columns: minmax(80px, max-content) 1fr;
  gap: 3px 12px;
  margin: 0;
  font-size: 11px;
}

.maps-detail-performance-tab__output-rows dt {
  color: var(--font-color-dimmed);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-detail-performance-tab__output-rows dd {
  color: var(--font-color);
  margin: 0;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.maps-detail-performance-tab__raw {
  border-top: 1px solid var(--default-border-color);
  padding-top: 6px;
}

.maps-detail-performance-tab__raw > summary {
  cursor: pointer;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: var(--font-weight-bold);
  padding: 4px 0;
  user-select: none;
}

.maps-detail-performance-tab__raw[open] > summary {
  color: var(--font-color);
}

.maps-detail-performance-tab__rows {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin-top: 6px;
}

.maps-detail-performance-tab__row {
  display: grid;
  grid-template-columns: 80px 1fr 90px;
  gap: var(--dimension-4);
  align-items: center;
  font-size: 11px;
}

.maps-detail-performance-tab__row-label {
  color: var(--font-color-dimmed);
  text-transform: uppercase;
  font-size: 9px;
  letter-spacing: 0.04em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-detail-performance-tab__row-value {
  color: var(--font-color);
  text-align: right;
  font-variant-numeric: tabular-nums;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
