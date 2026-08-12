<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import { type RankedTableCellRender } from '@/dashboard/components/CmkRankedTable'

import codeExample from './UclCmkRankedTableCodeExample.vue?raw'

export const panelConfig = {
  barColor: {
    type: 'list' as const,
    title: 'Bar color',
    help: 'CSS color of the inline bars. A cell may override it with its own `color`.',
    options: [
      { title: 'Blue', name: 'var(--color-light-blue-50)' },
      { title: 'Green', name: 'var(--color-corporate-green-50)' },
      { title: 'Grey', name: 'var(--color-mid-grey-50)' },
      { title: 'Magenta', name: 'var(--color-pink-50)' },
      { title: 'Orange', name: 'var(--color-orange-50)' },
      { title: 'Purple', name: 'var(--color-purple-50)' },
      { title: 'Red', name: 'var(--color-light-red-50)' },
      { title: 'Yellow', name: 'var(--color-yellow-50)' }
    ],
    initialState: 'var(--color-corporate-green-50)' as const
  },
  containerHeight: {
    type: 'number' as const,
    title: 'Container height (px)',
    help: 'Height of the scrollable box around the table. The table keeps its rows at full size and scrolls once they no longer fit.',
    initialState: 220
  },
  rowCount: {
    type: 'number' as const,
    title: 'Rows',
    initialState: 6
  },
  valueBar: {
    type: 'boolean' as const,
    title: 'Show bar',
    help: 'Renders the value column as a bar with its value beside it, instead of plain text.',
    initialState: true
  },
  valueRender: {
    type: 'list' as const,
    title: 'Value rendering',
    help: 'Bytes are formatted as SI values, count is right-aligned as-is, text is left-aligned.',
    options: [
      { title: 'Bytes', name: 'bytes' },
      { title: 'Count', name: 'count' },
      { title: 'Text', name: 'text' }
    ] satisfies Options<RankedTableCellRender>[],
    initialState: 'bytes' as const
  },
  fixedBarRange: {
    type: 'boolean' as const,
    title: 'Fixed bar range',
    help: 'Scales the bars against a fixed 0 - 250 GB range, clamped to it, instead of against the largest value in the column.',
    initialState: false
  },
  preFormatted: {
    type: 'boolean' as const,
    title: 'Pre-formatted values',
    help: "Gives each cell a ready-made `formatted` text, which wins over the column's rendering.",
    initialState: false
  },
  perRowColor: {
    type: 'boolean' as const,
    title: 'Per-row bar colors',
    help: 'Each cell carries its own bar `color`, overriding the palette color above.',
    initialState: false
  },
  linkedHosts: {
    type: 'boolean' as const,
    title: 'Linked host cells',
    help: 'Cells with an `href` render as links.',
    initialState: false
  },
  clickableHosts: {
    type: 'boolean' as const,
    title: 'Clickable host cells',
    help: 'Cells of a `clickable` column render as buttons emitting `cellClick`.',
    initialState: false
  }
} satisfies PanelConfigFor<typeof CmkRankedTable, 'rows' | 'columns'> & {
  containerHeight: NumberPropDef
  rowCount: NumberPropDef
  valueBar: BoolPropDef
  valueRender: ListPropDef<RankedTableCellRender>
  fixedBarRange: BoolPropDef
  preFormatted: BoolPropDef
  perRowColor: BoolPropDef
  linkedHosts: BoolPropDef
  clickableHosts: BoolPropDef
}
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { computed, ref } from 'vue'

import CmkRankedTable, {
  type RankedTableColumn,
  type RankedTableRow
} from '@/dashboard/components/CmkRankedTable'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkRankedTable, 'rows' | 'columns'>().createRef(
  panelConfig
)

// Pre-ranked sample data; the panel decides how many of these rows are shown.
const HOSTS = [
  { host: '10.0.71.219', volume: 194_420_000_000, flows: 1284 },
  { host: '10.0.234.247', volume: 158_270_000_000, flows: 967 },
  { host: '10.0.171.51', volume: 58_270_000_000, flows: 411 },
  { host: '10.0.151.254', volume: 51_670_000_000, flows: 388 },
  { host: '10.0.198.27', volume: 27_380_000_000, flows: 154 },
  { host: '10.0.139.151', volume: 22_260_000_000, flows: 102 },
  { host: '10.0.104.62', volume: 18_940_000_000, flows: 97 },
  { host: '10.0.88.13', volume: 12_510_000_000, flows: 74 },
  { host: '10.0.57.201', volume: 9_330_000_000, flows: 61 },
  { host: '10.0.42.98', volume: 6_120_000_000, flows: 43 },
  { host: '10.0.31.7', volume: 3_870_000_000, flows: 28 },
  { host: '10.0.12.44', volume: 1_240_000_000, flows: 11 }
]

const ROW_COLORS = [
  'var(--color-light-red-50)',
  'var(--color-orange-50)',
  'var(--color-yellow-50)',
  'var(--color-corporate-green-50)'
]

const columns = computed<RankedTableColumn[]>(() => [
  {
    key: 'host',
    title: 'Host',
    render: 'text',
    bar: false,
    ...(propState.value.clickableHosts ? { clickable: true } : {})
  },
  {
    key: 'volume',
    title: 'Volume',
    render: propState.value.valueRender,
    bar: propState.value.valueBar,
    ...(propState.value.fixedBarRange ? { barRange: [0, 250_000_000_000] as [number, number] } : {})
  },
  { key: 'flows', title: 'Flows', render: 'count', bar: false }
])

const rows = computed<RankedTableRow[]>(() =>
  HOSTS.slice(0, Math.max(0, propState.value.rowCount)).map((entry, index) => ({
    host: propState.value.linkedHosts ? { value: entry.host, href: '#' } : entry.host,
    volume: {
      value: entry.volume,
      ...(propState.value.preFormatted
        ? { formatted: `~${Math.round(entry.volume / 1_000_000_000)} GB` }
        : {}),
      ...(propState.value.perRowColor ? { color: ROW_COLORS[index % ROW_COLORS.length]! } : {})
    },
    flows: entry.flows
  }))
)

const lastCellClick = ref<string | null>(null)

function onCellClick(column: RankedTableColumn, row: RankedTableRow): void {
  const cell = row[column.key]
  lastCellClick.value = `${column.key} = ${typeof cell === 'object' ? cell.value : cell}`
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkRankedTable</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        class="ucl-cmk-ranked-table__container"
        :style="{ height: `${Math.max(0, propState.containerHeight)}px` }"
      >
        <CmkRankedTable
          :columns="columns"
          :rows="rows"
          :bar-color="propState.barColor"
          @cell-click="onCellClick"
        />
      </div>
      <CmkParagraph v-if="lastCellClick">Last cellClick: {{ lastCellClick }}</CmkParagraph>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
/* The table sizes itself from its rows, so the box around it is what scrolls. */
.ucl-cmk-ranked-table__container {
  /* The preview area centers its children, so claim the full width explicitly --
     otherwise the box shrinks to the text columns and leaves the bar no room. */
  width: 100%;
  overflow: auto;
  resize: vertical;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
