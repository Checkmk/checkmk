<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import { userSpecificUnit } from '@/lib/unit-format/unitFormatter'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import type { ConsolidationFn, HorizontalLine, Metric } from './TimeSeriesGraph'

const { _t, _tn } = usei18n()

const CONSOLIDATION_FUNCTION_LABELS = computed(
  (): Record<ConsolidationFn, string> => ({
    min: _t('Min'),
    avg: _t('Average'),
    max: _t('Max')
  })
)

const props = withDefaults(
  defineProps<{
    metrics: Metric[]
    horizontalLines?: HorizontalLine[]
    consolidationFn?: ConsolidationFn
    hiddenMetricNames?: string[]
    hiddenLineNames?: string[]
  }>(),
  {
    horizontalLines: () => [],
    consolidationFn: 'avg',
    hiddenMetricNames: () => [],
    hiddenLineNames: () => []
  }
)

const emit = defineEmits<{
  // TODO: implement this emit through a dropdown for consolidation function selection
  'update:consolidationFn': [value: ConsolidationFn]
  'update:hiddenMetricNames': [value: string[]]
  'update:hiddenLineNames': [value: string[]]
  hoverMetric: [metricName: string | null]
  requestShowAll: []
}>()

const metricsString = computed(() =>
  _tn('%{n} metric', '%{n} metrics', props.metrics.length, { n: props.metrics.length })
)
const selectedCount = computed(() => props.metrics.length - props.hiddenMetricNames.length)

interface MetricStats {
  min: string
  avg: string
  max: string
  last: string
}

const metricStats = computed((): Map<string, MetricStats> => {
  const map = new Map<string, MetricStats>()
  for (const m of props.metrics) {
    const { formatter } = userSpecificUnit(m.metadata.unit, 'celsius')
    const fmt = (v: number) => formatter.render(v)
    const pts = m.data_points
    if (!pts || pts.length === 0) {
      map.set(m.metadata.name, { min: 'n/a', avg: 'n/a', max: 'n/a', last: 'n/a' })
      continue
    }
    let min = Infinity
    let max = -Infinity
    let sum = 0
    let count = 0
    for (const v of pts) {
      if (v !== null && isFinite(v)) {
        if (v < min) {
          min = v
        }
        if (v > max) {
          max = v
        }
        sum += v
        count++
      }
    }
    const last = pts[pts.length - 1]!
    map.set(m.metadata.name, {
      min: isFinite(min) ? fmt(min) : 'n/a',
      avg: count > 0 ? fmt(sum / count) : 'n/a',
      max: isFinite(max) ? fmt(max) : 'n/a',
      last: last !== null && isFinite(last) ? fmt(last) : 'n/a'
    })
  }
  return map
})

function toggleMetric(name: string) {
  const newHiddenNames = [...props.hiddenMetricNames]
  const idx = newHiddenNames.indexOf(name)
  if (idx >= 0) {
    newHiddenNames.splice(idx, 1)
  } else {
    newHiddenNames.push(name)
  }
  emit('update:hiddenMetricNames', newHiddenNames)
}

function toggleLine(name: string) {
  const newHiddenNames = [...props.hiddenLineNames]
  const idx = newHiddenNames.indexOf(name)
  if (idx >= 0) {
    newHiddenNames.splice(idx, 1)
  } else {
    newHiddenNames.push(name)
  }
  emit('update:hiddenLineNames', newHiddenNames)
}
</script>

<template>
  <table class="graphing-graph-legend">
    <colgroup>
      <col class="graphing-graph-legend__col--eye" />
      <col class="graphing-graph-legend__col--swatch" />
      <col />
      <col class="graphing-graph-legend__col--stat" />
      <col class="graphing-graph-legend__col--stat" />
      <col class="graphing-graph-legend__col--stat" />
      <col class="graphing-graph-legend__col--stat" />
    </colgroup>

    <thead>
      <tr class="graphing-graph-legend__header-row">
        <th colspan="3">
          <div class="graphing-graph-legend__header-meta">
            <button
              v-if="metrics.length > 9"
              class="graphing-graph-legend__metric-count-btn"
              :title="_t('Show all metrics')"
              @click="$emit('requestShowAll')"
            >
              {{ metricsString }}
            </button>
            <span v-else class="graphing-graph-legend__metric-count">{{ metricsString }}</span>
            <span class="graphing-graph-legend__selected-count">{{
              _tn('%{n} selected', '%{n} selected', selectedCount, { n: selectedCount })
            }}</span>
          </div>
        </th>
        <th
          v-for="cfn in ['min', 'avg', 'max'] as ConsolidationFn[]"
          :key="cfn"
          class="graphing-graph-legend__consolidation-function-th"
        >
          {{ CONSOLIDATION_FUNCTION_LABELS[cfn] }}
        </th>
        <th class="graphing-graph-legend__last-header">{{ _t('Last') }}</th>
      </tr>
    </thead>

    <!-- "Show all" row for 10+ metrics -->
    <tbody v-if="metrics.length > 9">
      <tr>
        <td colspan="7" class="graphing-graph-legend__show-all-cell">
          <button class="graphing-graph-legend__show-all" @click="$emit('requestShowAll')">
            {{ _t('Show all') }}
          </button>
        </td>
      </tr>
    </tbody>

    <!-- Metric rows -->
    <tbody>
      <tr
        v-for="m in metrics"
        :key="m.metadata.name"
        class="graphing-graph-legend__row"
        :class="{
          'graphing-graph-legend__row--hidden': hiddenMetricNames.includes(m.metadata.name)
        }"
        @mouseenter="$emit('hoverMetric', m.metadata.name)"
        @mouseleave="$emit('hoverMetric', null)"
      >
        <td class="graphing-graph-legend__cell--eye">
          <button class="graphing-graph-legend__eye-btn" @click="toggleMetric(m.metadata.name)">
            <CmkMultitoneIcon
              :name="hiddenMetricNames.includes(m.metadata.name) ? 'eye-crossed-out' : 'eye'"
              primary-color="font"
              size="small"
            />
          </button>
        </td>
        <td class="graphing-graph-legend__cell--swatch">
          <span class="graphing-graph-legend__swatch" :style="{ background: m.metadata.color }" />
        </td>
        <td class="graphing-graph-legend__name" :title="m.metadata.title">
          {{ m.metadata.title }}
        </td>
        <td class="graphing-graph-legend__stat">{{ metricStats.get(m.metadata.name)?.min }}</td>
        <td class="graphing-graph-legend__stat">{{ metricStats.get(m.metadata.name)?.avg }}</td>
        <td class="graphing-graph-legend__stat">{{ metricStats.get(m.metadata.name)?.max }}</td>
        <td class="graphing-graph-legend__stat">{{ metricStats.get(m.metadata.name)?.last }}</td>
      </tr>
    </tbody>

    <!-- Horizontal line rows — border-top on the section separates it from metric rows -->
    <tbody v-if="horizontalLines.length > 0" class="graphing-graph-legend__lines-section">
      <tr
        v-for="line in horizontalLines"
        :key="line.name"
        class="graphing-graph-legend__row"
        :class="{ 'graphing-graph-legend__row--hidden': hiddenLineNames.includes(line.name) }"
      >
        <td class="graphing-graph-legend__cell--eye">
          <button class="graphing-graph-legend__eye-btn" @click="toggleLine(line.name)">
            <CmkMultitoneIcon
              :name="hiddenLineNames.includes(line.name) ? 'eye-crossed-out' : 'eye'"
              primary-color="font"
              size="small"
            />
          </button>
        </td>
        <td class="graphing-graph-legend__cell--swatch">
          <span class="graphing-graph-legend__swatch" :style="{ background: line.color }" />
        </td>
        <td class="graphing-graph-legend__name">{{ line.name }}</td>
        <td></td>
        <td></td>
        <td></td>
        <td class="graphing-graph-legend__stat">{{ line.value }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped lang="scss">
.graphing-graph-legend {
  font-size: var(--font-size-small);
  color: var(--font-color);
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;

  th,
  td {
    padding: 2px;
    vertical-align: middle;
  }
}

// Column widths — col 3 (name) gets no explicit width and fills remaining space
.graphing-graph-legend__col--eye {
  width: 20px;
}
.graphing-graph-legend__col--swatch {
  width: 10px;
}
.graphing-graph-legend__col--stat {
  width: 64px;
}

.graphing-graph-legend__header-row {
  border-bottom: 1px solid var(--ux-theme-6, #e0e0e0);

  th {
    padding-top: 4px;
    padding-bottom: 6px;
    text-align: right;
    font-weight: normal;
  }
}

.graphing-graph-legend__header-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.graphing-graph-legend__metric-count {
  font-weight: var(--font-weight-bold);
}

.graphing-graph-legend__metric-count-btn {
  font-weight: var(--font-weight-bold);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--font-color);
  text-decoration: underline;
  font-size: inherit;

  &:hover {
    opacity: 0.7;
  }
}

.graphing-graph-legend__selected-count {
  opacity: 0.55;
}

.graphing-graph-legend__last-header {
  opacity: 0.6;
}

.graphing-graph-legend__show-all-cell {
  padding: 0;
}

.graphing-graph-legend__show-all {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 4px 0;
  cursor: pointer;
  color: var(--font-color);
  font-size: inherit;
  text-decoration: underline;
  opacity: 0.7;

  &:hover {
    opacity: 1;
  }
}

.graphing-graph-legend__row {
  &:hover {
    background: rgb(0 0 0 / 4%);
  }

  &--hidden {
    opacity: 0.45;
  }
}

.graphing-graph-legend__cell--eye {
  text-align: center;
}

.graphing-graph-legend__cell--swatch {
  text-align: center;
}

.graphing-graph-legend__eye-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  border-radius: var(--border-radius);
  margin: 0 auto;

  &:hover {
    background: rgb(0 0 0 / 8%);
  }
}

.graphing-graph-legend__swatch {
  display: inline-block;
  width: 4px;
  height: 10px;
  border-radius: 2px;
}

.graphing-graph-legend__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-graph-legend td.graphing-graph-legend__stat {
  padding-right: 4px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}

// Section divider: border-top on the first row's cells replaces the standalone divider element
.graphing-graph-legend__lines-section > tr:first-child > td {
  border-top: 1px solid var(--ux-theme-6, #e0e0e0);
  padding-top: 8px;
}
</style>
