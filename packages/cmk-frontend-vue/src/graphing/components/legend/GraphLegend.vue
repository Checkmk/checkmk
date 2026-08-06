<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'

import type { HorizontalLine, Metric } from '../TimeSeriesGraph'
import {
  CONSOLIDATION_FUNCTIONS,
  type ConsolidationFn,
  useConsolidationFunctionLabels
} from '../consolidation'
import GraphLegendEyeButton from './GraphLegendEyeButton.vue'
import {
  type MetricStats,
  metricStats as computeMetricStats,
  horizontalLineValue,
  metricsInGraphTopToBottomOrder,
  withNameToggled
} from './legendUtils'

const { _t, _tn } = usei18n()

const consolidationFunctionLabels = useConsolidationFunctionLabels()

const props = withDefaults(
  defineProps<{
    metrics: Metric[]
    horizontalLines?: HorizontalLine[]
    consolidationFn?: ConsolidationFn
    hiddenMetricNames?: string[]
    hiddenLineNames?: string[]
    fillHeight?: boolean
  }>(),
  {
    horizontalLines: () => [],
    consolidationFn: 'avg',
    hiddenMetricNames: () => [],
    hiddenLineNames: () => [],
    fillHeight: false
  }
)

const emit = defineEmits<{
  // TODO: implement this emit through a dropdown for consolidation function selection
  'update:consolidationFn': [value: ConsolidationFn]
  'update:hiddenMetricNames': [value: string[]]
  'update:hiddenLineNames': [value: string[]]
  hoverMetric: [metricName: string | null]
}>()

const metricsString = computed(() =>
  _tn('%{n} metric', '%{n} metrics', props.metrics.length, { n: props.metrics.length })
)
const selectedCount = computed(() => props.metrics.length - props.hiddenMetricNames.length)

const displayMetrics = computed(() => metricsInGraphTopToBottomOrder(props.metrics))
const allHidden = computed(
  () =>
    props.metrics.length > 0 &&
    props.metrics.every((m) => props.hiddenMetricNames.includes(m.metadata.name))
)

function toggleAll() {
  if (allHidden.value) {
    emit('update:hiddenMetricNames', [])
  } else {
    emit(
      'update:hiddenMetricNames',
      props.metrics.map((m) => m.metadata.name)
    )
  }
}

const metricStats = computed((): Map<string, MetricStats> => {
  const map = new Map<string, MetricStats>()
  for (const m of props.metrics) {
    map.set(m.metadata.name, computeMetricStats(m))
  }
  return map
})

function toggleMetric(name: string) {
  emit('update:hiddenMetricNames', withNameToggled(props.hiddenMetricNames, name))
}

function toggleLine(name: string) {
  emit('update:hiddenLineNames', withNameToggled(props.hiddenLineNames, name))
}

const metricsTableRef = useTemplateRef<HTMLTableElement>('metricsTable')
const scrollContainerRef = computed(() => metricsTableRef.value?.parentElement ?? null)
const metricsScrollable = ref(false)

function updateScrollable() {
  const el = scrollContainerRef.value
  metricsScrollable.value = el ? el.scrollHeight > el.clientHeight : false
}

const { observe } = useResizeObserver(updateScrollable)
observe(metricsTableRef)
observe(scrollContainerRef)

onMounted(async () => {
  await nextTick()
  updateScrollable()
})

watch(
  () => props.metrics.length,
  async () => {
    await nextTick()
    updateScrollable()
  }
)
</script>

<template>
  <div class="graphing-graph-legend" :class="{ 'graphing-graph-legend--fill': fillHeight }">
    <!-- Table 1: fixed header row -->
    <table class="graphing-graph-legend__table">
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
        <tr
          class="graphing-graph-legend__header-row"
          :class="{ 'graphing-graph-legend__padded-row': metricsScrollable }"
        >
          <th>
            <GraphLegendEyeButton
              :hidden="allHidden"
              :title="allHidden ? _t('Show all') : _t('Hide all')"
              @toggle="toggleAll"
            />
          </th>
          <th colspan="2">
            <div class="graphing-graph-legend__header-meta">
              <button
                class="graphing-graph-legend__metric-count-btn"
                :title="allHidden ? _t('Show all metrics') : _t('Hide all metrics')"
                @click="toggleAll"
              >
                {{ metricsString }}
              </button>
              <span class="graphing-graph-legend__selected-count">{{
                _tn('%{n} selected', '%{n} selected', selectedCount, { n: selectedCount })
              }}</span>
            </div>
          </th>
          <th
            v-for="consolidationFunction in CONSOLIDATION_FUNCTIONS"
            :key="consolidationFunction"
            class="graphing-graph-legend__consolidation-function-th"
          >
            {{ consolidationFunctionLabels[consolidationFunction] }}
          </th>
          <th class="graphing-graph-legend__last-header">
            {{ _t('Last') }}
          </th>
        </tr>
      </thead>
    </table>

    <!-- Table 2: metric rows — scrollable -->
    <CmkScrollContainer
      class="graphing-graph-legend__rows-scroll"
      :max-height="fillHeight ? 'none' : '500px'"
      height="auto"
      :style="{ overflowX: 'hidden' }"
    >
      <table
        ref="metricsTable"
        class="graphing-graph-legend__table graphing-graph-legend__table-metrics"
      >
        <colgroup>
          <col class="graphing-graph-legend__col--eye" />
          <col class="graphing-graph-legend__col--swatch" />
          <col />
          <col class="graphing-graph-legend__col--stat" />
          <col class="graphing-graph-legend__col--stat" />
          <col class="graphing-graph-legend__col--stat" />
          <col class="graphing-graph-legend__col--stat" />
        </colgroup>
        <tbody>
          <tr
            v-for="m in displayMetrics"
            :key="m.metadata.name"
            class="graphing-graph-legend__row"
            :class="{
              'graphing-graph-legend__row--hidden': hiddenMetricNames.includes(m.metadata.name)
            }"
            @mouseenter="$emit('hoverMetric', m.metadata.name)"
            @mouseleave="$emit('hoverMetric', null)"
          >
            <td class="graphing-graph-legend__cell--eye">
              <GraphLegendEyeButton
                :hidden="hiddenMetricNames.includes(m.metadata.name)"
                :aria-label="m.metadata.title"
                @toggle="toggleMetric(m.metadata.name)"
              />
            </td>
            <td class="graphing-graph-legend__cell--swatch">
              <span
                class="graphing-graph-legend__swatch"
                :style="{ background: m.metadata.color }"
              />
            </td>
            <td class="graphing-graph-legend__name" :title="m.metadata.title">
              {{ m.metadata.title }}
            </td>
            <td class="graphing-graph-legend__stat">
              {{ metricStats.get(m.metadata.name)?.min }}
            </td>
            <td class="graphing-graph-legend__stat">
              {{ metricStats.get(m.metadata.name)?.avg }}
            </td>
            <td class="graphing-graph-legend__stat">
              {{ metricStats.get(m.metadata.name)?.max }}
            </td>
            <td class="graphing-graph-legend__stat">
              {{ metricStats.get(m.metadata.name)?.last }}
            </td>
          </tr>
        </tbody>
      </table>
    </CmkScrollContainer>

    <!-- Table 3: horizontal lines — not scrollable, only rendered when lines are present -->
    <table
      v-if="horizontalLines.length > 0"
      class="graphing-graph-legend__table graphing-graph-legend__lines-table"
    >
      <colgroup>
        <col class="graphing-graph-legend__col--eye" />
        <col class="graphing-graph-legend__col--swatch" />
        <col />
        <col class="graphing-graph-legend__col--stat" />
        <col class="graphing-graph-legend__col--stat" />
        <col class="graphing-graph-legend__col--stat" />
        <col class="graphing-graph-legend__col--stat" />
      </colgroup>
      <tbody>
        <tr
          v-for="line in horizontalLines"
          :key="line.name"
          class="graphing-graph-legend__row"
          :class="{
            'graphing-graph-legend__row--hidden': hiddenLineNames.includes(line.name),
            'graphing-graph-legend__padded-row': metricsScrollable
          }"
        >
          <td class="graphing-graph-legend__cell--eye">
            <GraphLegendEyeButton
              :hidden="hiddenLineNames.includes(line.name)"
              :aria-label="line.title"
              @toggle="toggleLine(line.name)"
            />
          </td>
          <td class="graphing-graph-legend__cell--swatch">
            <span class="graphing-graph-legend__swatch" :style="{ background: line.color }" />
          </td>
          <td class="graphing-graph-legend__name">{{ line.title }}</td>
          <td></td>
          <td></td>
          <td></td>
          <td class="graphing-graph-legend__stat">
            {{ horizontalLineValue(line) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-legend {
  font-size: var(--font-size-small);
  color: var(--font-color);
  width: 100%;
}

.graphing-graph-legend--fill {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;

  > .graphing-graph-legend__table {
    flex-shrink: 0;
  }

  .graphing-graph-legend__rows-scroll {
    flex: 1 1 auto;
    min-height: 0;
  }
}

.graphing-graph-legend__table {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;

  th,
  td {
    padding: 2px;
    vertical-align: middle;
  }

  .graphing-graph-legend__padded-row th,
  .graphing-graph-legend__padded-row td {
    padding-right: var(--spacing);
  }
}

.graphing-graph-legend__table-metrics {
  margin-right: var(--spacing);
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

.graphing-graph-legend__lines-table {
  border-top: 1px solid var(--ux-theme-6, #e0e0e0);
  padding-top: 8px;
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

.graphing-graph-legend :deep(.graphing-graph-legend-eye-button) {
  margin: 0 auto;
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
  text-align: right;
  font-variant-numeric: tabular-nums;
  opacity: 0.8;
}
</style>
