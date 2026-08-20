<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ColumnDef } from '@tanstack/vue-table'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import EditableTable from '@/monitoring/shared/components/EditableTable.vue'
import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'
import CollapsibleCell from '@/monitoring/shared/components/cell/CollapsibleCell.vue'
import ColorPickerCell from '@/monitoring/shared/components/cell/ColorPickerCell.vue'
import DragHandleCell from '@/monitoring/shared/components/cell/DragHandleCell.vue'
import DropdownCell from '@/monitoring/shared/components/cell/DropdownCell.vue'
import SwitchCell from '@/monitoring/shared/components/cell/SwitchCell.vue'
import VisibilityCell from '@/monitoring/shared/components/cell/VisibilityCell.vue'

import MetricAttributesTable from '../../components/MetricAttributesTable.vue'
import type { Metric } from '../../components/TimeSeriesGraph'
import {
  type MetricStats,
  metricStats,
  orderMetricsForLegend
} from '../../components/legend/legendUtils'
import { attributesOf, hasAttributes } from '../../components/metricAttributes'
import { type GraphItemsStore, retainKnownRows } from '../composables/useGraphItems'
import { useRowLabels } from '../composables/useRowLabels'
import type { DesignerItem } from '../drafts'
import { type ItemId, isSingleLine, parseLineType } from '../types'
import StatsCells from './StatsCells.vue'

const { store, metricsBySource, resolvedTitles } = defineProps<{
  store: GraphItemsStore
  /** Fetched series per data-source row, for the live-data columns. */
  metricsBySource: Map<ItemId, Metric[]>
  /** The title each row resolved to in the last fetch; rows that resolved to none are absent. */
  resolvedTitles: ReadonlyMap<ItemId, string>
}>()

const { _t } = usei18n()
const { sourceTypeLabel, lineStyleSuggestions, lineStyleLabel } = useRowLabels()

const columns: ColumnDef<DesignerItem>[] = [
  { id: 'drag', header: '', meta: { justify: 'center' } },
  { id: 'visibility', header: '', meta: { justify: 'center' } },
  { id: 'id', header: _t('ID'), meta: { justify: 'left' } },
  { id: 'source', header: _t('Source'), meta: { justify: 'left' } },
  { id: 'color', header: _t('Color'), meta: { justify: 'center' } },
  { id: 'title', header: _t('Title'), minSize: 200, meta: { stretch: true } },
  { id: 'line_style', header: _t('Line style'), meta: { justify: 'left' } },
  { id: 'mirrored', header: _t('Mirrored'), meta: { justify: 'center' } },
  { id: 'min', header: _t('Min'), meta: { justify: 'right' } },
  { id: 'avg', header: _t('Average'), meta: { justify: 'right' } },
  { id: 'max', header: _t('Max'), meta: { justify: 'right' } },
  { id: 'last', header: _t('Last'), meta: { justify: 'right' } }
]

const colorColumnIndex = columns.findIndex((column) => column.id === 'color')

const expandedRows = ref<Record<string, boolean>>({})

function isExpanded(row: DesignerItem): boolean {
  return !isSingleLine(row) && (expandedRows.value[row.id] ?? true)
}

watch(
  () => store.items.value,
  (rows) => {
    expandedRows.value = retainKnownRows(expandedRows.value, rows)
  }
)

/** Second expansion level: the attributes of a single resolved series. */
const expandedSeries = ref<Record<string, boolean>>({})

/** Row-qualified in case metric names stop being unique per response. */
function seriesKey(rowId: ItemId, metric: Metric): string {
  return `${rowId}:${metric.metadata.name}`
}

/** Guards an expanded row whose series came back without attributes. */
function showsAttributes(rowId: ItemId, metric: Metric): boolean {
  return hasAttributes(metric) && expandedSeries.value[seriesKey(rowId, metric)] === true
}

/** Row stats are only attributable when the row produced exactly one series. */
const statsBySource = computed(() => {
  const stats = new Map<ItemId, MetricStats>()
  for (const [id, series] of metricsBySource) {
    if (series.length === 1) {
      stats.set(id, metricStats(series[0]!))
    }
  }
  return stats
})

/** Per source: its resolved lines in legend order, each with pre-formatted stats. */
const linesBySource = computed(() => {
  const out = new Map<ItemId, { metric: Metric; stats: MetricStats }[]>()
  for (const [id, series] of metricsBySource) {
    out.set(
      id,
      orderMetricsForLegend([...series]).map((metric) => ({
        metric,
        stats: metricStats(metric)
      }))
    )
  }
  return out
})

function onLineStyleChange(row: DesignerItem, value: string | null): void {
  const lineType = parseLineType(value)
  if (lineType !== undefined) {
    store.patch(row.id, { line_type: lineType })
  }
}
</script>

<template>
  <CmkScrollContainer
    height="auto"
    max-height="none"
    class="graphing-appearance-table"
    :style="{ overflow: 'var(--graphing-designer-body-table-overflow, auto)' }"
  >
    <EditableTable
      :rows="[...store.items.value]"
      :columns="columns"
      :get-row-key="(row: DesignerItem) => row.id"
      :is-row-expanded="isExpanded"
      @reorder="(from: number, to: number) => store.move(from, to)"
    >
      <template #row="{ row }">
        <DragHandleCell column-id="drag" vertical-align="middle" />
        <VisibilityCell
          column-id="visibility"
          vertical-align="middle"
          :model-value="row.visible"
          @update:model-value="store.setVisibility([row.id], $event)"
        />
        <BaseCell column-id="id" vertical-align="middle" no-wrap>{{ row.id }}</BaseCell>
        <BaseCell column-id="source" vertical-align="middle" no-wrap>{{
          sourceTypeLabel(row.type)
        }}</BaseCell>
        <ColorPickerCell
          v-if="isSingleLine(row)"
          column-id="color"
          vertical-align="middle"
          :model-value="row.color"
          @update:model-value="store.patch(row.id, { color: $event })"
        />
        <BaseCell v-else column-id="color" vertical-align="middle" />
        <BaseCell v-if="isSingleLine(row)" column-id="title" vertical-align="middle" no-wrap>{{
          resolvedTitles.get(row.id) ?? row.title
        }}</BaseCell>
        <CollapsibleCell
          v-else
          column-id="title"
          vertical-align="middle"
          :expanded="isExpanded(row)"
          @update:expanded="expandedRows = { ...expandedRows, [row.id]: $event }"
          >{{ resolvedTitles.get(row.id) ?? row.title }}</CollapsibleCell
        >
        <DropdownCell
          column-id="line_style"
          vertical-align="middle"
          :model-value="row.line_type"
          :options="lineStyleSuggestions"
          :label="lineStyleLabel"
          @update:model-value="onLineStyleChange(row, $event)"
        />
        <SwitchCell
          column-id="mirrored"
          vertical-align="middle"
          :model-value="row.mirrored"
          @update:model-value="store.patch(row.id, { mirrored: $event })"
        />
        <StatsCells :stats="statsBySource.get(row.id)" />
      </template>

      <template #expansion="{ row }">
        <template
          v-for="entry in linesBySource.get(row.id) ?? []"
          :key="entry.metric.metadata.name"
        >
          <tr class="graphing-appearance-table__expanded-row">
            <td :colspan="colorColumnIndex" />
            <BaseCell column-id="color" vertical-align="middle">
              <span
                class="graphing-appearance-table__color-swatch"
                :style="{ background: entry.metric.metadata.color }"
              />
            </BaseCell>
            <CollapsibleCell
              v-if="hasAttributes(entry.metric)"
              column-id="title"
              vertical-align="middle"
              :expanded="expandedSeries[seriesKey(row.id, entry.metric)] === true"
              @update:expanded="
                expandedSeries = {
                  ...expandedSeries,
                  [seriesKey(row.id, entry.metric)]: $event
                }
              "
              >{{ entry.metric.metadata.title }}</CollapsibleCell
            >
            <BaseCell v-else column-id="title" vertical-align="middle" no-wrap>{{
              entry.metric.metadata.title
            }}</BaseCell>
            <td :colspan="2" />
            <StatsCells :stats="entry.stats" />
          </tr>
          <tr v-if="showsAttributes(row.id, entry.metric)">
            <td :colspan="columns.length" class="graphing-appearance-table__attributes">
              <MetricAttributesTable :attributes="attributesOf(entry.metric)" />
            </td>
          </tr>
        </template>
      </template>

      <template #empty-state>
        {{ _t('This graph has no data sources yet.') }}
      </template>
    </EditableTable>
  </CmkScrollContainer>
</template>

<style scoped>
.graphing-appearance-table {
  flex: 0 1 auto;
  min-height: 0;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
.graphing-appearance-table__expanded-row :deep(td) {
  background-color: var(--ux-theme-3);
}

.graphing-appearance-table__attributes {
  padding: var(--dimension-4) var(--dimension-4) var(--dimension-5) var(--dimension-8);
  background-color: var(--ux-theme-3);
}

.graphing-appearance-table__color-swatch {
  display: inline-block;
  width: var(--dimension-6);
  height: var(--dimension-6);
  border-radius: var(--border-radius);
}
</style>
