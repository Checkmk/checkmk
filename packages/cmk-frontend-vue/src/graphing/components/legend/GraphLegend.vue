<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'

import MetricAttributesTable from '../MetricAttributesTable.vue'
import type { HorizontalLine, Metric } from '../TimeSeriesGraph'
import {
  CONSOLIDATION_FUNCTIONS,
  type ConsolidationFn,
  DEFAULT_CONSOLIDATION_FN,
  useConsolidationFunctionLabels
} from '../consolidation'
import { attributesOf, hasAttributes } from '../metricAttributes'
import GraphLegendEyeButton from './GraphLegendEyeButton.vue'
import {
  type MetricStats,
  metricStats as computeMetricStats,
  horizontalLineValue,
  orderMetricsForLegend,
  withNameToggled
} from './legendUtils'

const { _t, _tn } = usei18n()

const componentId = useId()

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
    consolidationFn: DEFAULT_CONSOLIDATION_FN,
    hiddenMetricNames: () => [],
    hiddenLineNames: () => [],
    fillHeight: false
  }
)

const emit = defineEmits<{
  'update:hiddenMetricNames': [value: string[]]
  'update:hiddenLineNames': [value: string[]]
  hoverMetric: [metricName: string | null]
}>()

const visibleCount = computed(() => props.metrics.length - props.hiddenMetricNames.length)
const visibilityLabel = computed(() =>
  _tn(
    '%{visible} of %{total} metric is visible',
    '%{visible} of %{total} metrics are visible',
    props.metrics.length,
    { visible: visibleCount.value, total: props.metrics.length }
  )
)

// Counts threshold lines too: 5 metrics plus 2 thresholds scrolls where 7 metrics would.
const VISIBLE_ITEM_BUDGET = 7
const ROW_HEIGHT_PX = 24
const rowHeight = `${ROW_HEIGHT_PX}px`

const metricsMaxHeight = computed(() => {
  if (props.fillHeight) {
    return 'none'
  }
  const rowsForMetrics = Math.max(1, VISIBLE_ITEM_BUDGET - props.horizontalLines.length)
  return `${rowsForMetrics * ROW_HEIGHT_PX}px`
})

const displayMetrics = computed(() => orderMetricsForLegend(props.metrics))
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

const expandedMetricNames = ref<string[]>([])

function toggleAttributes(name: string) {
  expandedMetricNames.value = withNameToggled(expandedMetricNames.value, name)
}

function attributesId(index: number): string {
  return `${componentId}-attributes-${index}`
}

/** Guards an expanded row whose metric came back without attributes. */
function showsAttributes(metric: Metric): boolean {
  return hasAttributes(metric) && expandedMetricNames.value.includes(metric.metadata.name)
}

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
  <div
    class="graphing-graph-legend"
    :class="{ 'graphing-graph-legend--fill': fillHeight }"
    :style="{ '--legend-row-height': rowHeight }"
  >
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
          <th class="graphing-graph-legend__header--eye">
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
                {{ visibilityLabel }}
              </button>
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
      :max-height="metricsMaxHeight"
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
          <template v-for="(m, index) in displayMetrics" :key="m.metadata.name">
            <tr
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
              <td class="graphing-graph-legend__name">
                <span class="graphing-graph-legend__title" :title="m.metadata.title">
                  {{ m.metadata.title }}
                </span>
                <CmkIconButton
                  v-if="hasAttributes(m)"
                  class="graphing-graph-legend__attributes-toggle"
                  :name="showsAttributes(m) ? 'chevron-up' : 'chevron-down'"
                  primary-color="font"
                  size="small"
                  :aria-expanded="showsAttributes(m)"
                  :aria-controls="attributesId(index)"
                  :aria-label="_t('Toggle attributes of %{metric}', { metric: m.metadata.title })"
                  @click="toggleAttributes(m.metadata.name)"
                />
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
            <tr v-if="showsAttributes(m)">
              <td :id="attributesId(index)" colspan="7" class="graphing-graph-legend__attributes">
                <MetricAttributesTable :attributes="attributesOf(m)" />
              </td>
            </tr>
          </template>
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
  --swatch-gap: var(--dimension-4);
  --swatch-width: 4px;

  box-sizing: border-box;
  padding: var(--dimension-5);
  background: var(--ux-theme-2);
  font-size: var(--font-size-normal);
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
  width: calc(var(--swatch-gap) + var(--swatch-width));
}
.graphing-graph-legend__col--stat {
  width: 64px;
}

.graphing-graph-legend__header-row {
  border-bottom: 1px solid var(--ux-theme-6);

  th {
    padding-top: var(--dimension-3);
    padding-bottom: var(--dimension-5);
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

.graphing-graph-legend__lines-table {
  border-top: 1px solid var(--ux-theme-6);
  padding-top: 8px;
  background: var(--ux-theme-3);
}

.graphing-graph-legend__row {
  height: var(--legend-row-height);

  &:hover {
    background: var(--graphing-legend-row-hover);
  }

  &--hidden .graphing-graph-legend__name,
  &--hidden .graphing-graph-legend__stat {
    color: var(--graphing-legend-hidden-color);
  }
}

/* The eye button fills its column exactly, so with no cell padding the swatch cell's own
   padding is the gap between the two. The element qualifier beats the table's blanket rule. */
.graphing-graph-legend th.graphing-graph-legend__header--eye,
.graphing-graph-legend td.graphing-graph-legend__cell--eye {
  padding-left: 0;
  padding-right: 0;
  text-align: center;
}

.graphing-graph-legend td.graphing-graph-legend__cell--swatch {
  padding-left: var(--swatch-gap);
  padding-right: 0;
  text-align: left;
}

.graphing-graph-legend :deep(.graphing-graph-legend-eye-button) {
  margin: 0 auto;
}

.graphing-graph-legend__swatch {
  display: inline-block;
  width: var(--swatch-width);
  height: 16px;
  border-radius: var(--border-radius-half);
}

.graphing-graph-legend td.graphing-graph-legend__name {
  padding-left: var(--dimension-4);
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

/* The title, not its cell, is what ellipsises, so the toggle stays visible next to it. */
.graphing-graph-legend__title {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-graph-legend__attributes-toggle {
  flex: 0 0 auto;
}

.graphing-graph-legend td.graphing-graph-legend__attributes {
  padding: var(--dimension-5) 0 var(--dimension-5) var(--dimension-8);
  background: var(--ux-theme-3);
}

.graphing-graph-legend td.graphing-graph-legend__stat {
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

body[data-theme='facelift'] .graphing-graph-legend {
  --graphing-legend-hidden-color: var(--color-conference-grey-70);
  --graphing-legend-row-hover: var(--ux-theme-4);
}

body[data-theme='modern-dark'] .graphing-graph-legend {
  --graphing-legend-hidden-color: var(--color-white-70);
  --graphing-legend-row-hover: var(--color-white-10);
}
</style>
