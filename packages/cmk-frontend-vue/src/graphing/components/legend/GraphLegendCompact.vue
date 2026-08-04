<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { HorizontalLine, Metric } from '../TimeSeriesGraph'
import GraphLegendEyeButton from './GraphLegendEyeButton.vue'
import { metricsInGraphTopToBottomOrder, withNameToggled } from './legendUtils'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    metrics: Metric[]
    horizontalLines?: HorizontalLine[]
    hiddenMetricNames?: string[]
    hiddenLineNames?: string[]
  }>(),
  {
    horizontalLines: () => [],
    hiddenMetricNames: () => [],
    hiddenLineNames: () => []
  }
)

const emit = defineEmits<{
  'update:hiddenMetricNames': [value: string[]]
  'update:hiddenLineNames': [value: string[]]
  hoverMetric: [metricName: string | null]
}>()

const DISTINCTIVE_TAIL_CHARS = 5
const MIN_VISIBLE_HEAD_CHARS = 12
const ESTIMATED_CHAR_WIDTH_EM = 0.45

const EYE_BUTTON_WIDTH_PX = 20
const ITEM_GAP_PX = 2
const SWATCH_WIDTH_PX = 4
const SERIES_GAP_PX = 5
const ITEM_CHROME_WIDTH_PX = EYE_BUTTON_WIDTH_PX + ITEM_GAP_PX + SWATCH_WIDTH_PX + SERIES_GAP_PX

function splitForMiddleTruncation(title: string): { nameHead: string; nameTail: string } {
  if (title.length <= DISTINCTIVE_TAIL_CHARS * 2) {
    return { nameHead: title, nameTail: '' }
  }
  return {
    nameHead: title.slice(0, -DISTINCTIVE_TAIL_CHARS),
    nameTail: title.slice(-DISTINCTIVE_TAIL_CHARS)
  }
}

function itemMinWidth(nameHead: string, nameTail: string): string {
  const alwaysVisibleChars = Math.min(MIN_VISIBLE_HEAD_CHARS, nameHead.length) + nameTail.length
  return `calc(${ITEM_CHROME_WIDTH_PX}px + ${alwaysVisibleChars * ESTIMATED_CHAR_WIDTH_EM}em)`
}

interface CompactLegendItem {
  key: string
  title: string
  nameHead: string
  nameTail: string
  minWidth: string
  color: string
  hidden: boolean
  metricName: string | null
  toggle: () => void
}

function withTruncationLayout(
  item: Omit<CompactLegendItem, 'nameHead' | 'nameTail' | 'minWidth'>
): CompactLegendItem {
  const { nameHead, nameTail } = splitForMiddleTruncation(item.title)
  return { ...item, nameHead, nameTail, minWidth: itemMinWidth(nameHead, nameTail) }
}

const items = computed((): CompactLegendItem[] => [
  ...metricsInGraphTopToBottomOrder(props.metrics).map((metric) =>
    withTruncationLayout({
      key: `metric:${metric.metadata.name}`,
      title: metric.metadata.title,
      color: metric.metadata.color,
      hidden: props.hiddenMetricNames.includes(metric.metadata.name),
      metricName: metric.metadata.name,
      toggle: () =>
        emit(
          'update:hiddenMetricNames',
          withNameToggled(props.hiddenMetricNames, metric.metadata.name)
        )
    })
  ),
  ...props.horizontalLines.map((line) =>
    withTruncationLayout({
      key: `line:${line.name}`,
      title: line.title,
      color: line.color,
      hidden: props.hiddenLineNames.includes(line.name),
      metricName: null,
      toggle: () =>
        emit('update:hiddenLineNames', withNameToggled(props.hiddenLineNames, line.name))
    })
  )
])

function onItemEnter(item: CompactLegendItem): void {
  if (item.metricName !== null) {
    emit('hoverMetric', item.metricName)
  }
}

function onItemLeave(item: CompactLegendItem): void {
  if (item.metricName !== null) {
    emit('hoverMetric', null)
  }
}
</script>

<template>
  <div class="graphing-graph-legend-compact" role="group" :aria-label="_t('Graph metrics')">
    <div
      v-for="item in items"
      :key="item.key"
      class="graphing-graph-legend-compact__item"
      :class="{ 'graphing-graph-legend-compact__item--hidden': item.hidden }"
      :style="{ minWidth: item.minWidth }"
      @mouseenter="onItemEnter(item)"
      @mouseleave="onItemLeave(item)"
    >
      <GraphLegendEyeButton
        :hidden="item.hidden"
        :aria-label="item.title"
        @toggle="item.toggle()"
      />
      <span class="graphing-graph-legend-compact__series" :title="item.title">
        <span class="graphing-graph-legend-compact__swatch" :style="{ background: item.color }" />
        <span class="graphing-graph-legend-compact__name">
          <span class="graphing-graph-legend-compact__name-head">{{ item.nameHead }}</span
          ><span class="graphing-graph-legend-compact__name-tail">{{ item.nameTail }}</span>
        </span>
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.graphing-graph-legend-compact {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--spacing-half);
  overflow-x: auto;
  padding-bottom: 4px;
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.graphing-graph-legend-compact__item {
  flex: 0 1 auto;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  border-radius: var(--border-radius);

  &:hover {
    background: rgb(0 0 0 / 4%);
  }

  &--hidden {
    opacity: 0.45;
  }

  > :deep(.graphing-graph-legend-eye-button) {
    flex: 0 0 auto;
  }
}

.graphing-graph-legend-compact__series {
  flex: 0 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-half);
}

.graphing-graph-legend-compact__swatch {
  flex: 0 0 auto;
  width: 4px;
  height: 16px;
  border-radius: var(--border-radius-half);
}

.graphing-graph-legend-compact__name {
  display: flex;
  min-width: 0;
}

.graphing-graph-legend-compact__name-head {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre;
}

.graphing-graph-legend-compact__name-tail {
  flex: 0 0 auto;
  white-space: pre;
}
</style>
