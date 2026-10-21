<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import { type RankedTableCellRender } from '@/dashboard/components/CmkRankedTable'

import codeExample from './UclCmkRankedTableCodeExample.vue?raw'

export const panelConfig = {
  containerHeight: {
    type: 'number' as const,
    title: 'Container height (px)',
    help: 'Height of the box around the table. The table keeps its rows at full size and scrolls once they no longer fit.',
    initialState: 220
  },
  containerWidth: {
    type: 'number' as const,
    title: 'Container width (px)',
    help: 'Width of the box around the table. Text cells truncate before any figure does. Drag the corner of the preview to change it.',
    initialState: 600
  },
  longHostNames: {
    type: 'boolean' as const,
    title: 'Long host names',
    help: 'Uses fully qualified host names instead of IP addresses.',
    initialState: false
  },
  serviceColumn: {
    type: 'boolean' as const,
    title: 'Service column',
    help: 'Adds a second text column.',
    initialState: false
  },
  longColumnTitles: {
    type: 'boolean' as const,
    title: 'Long column titles',
    help: 'Uses column titles longer than their narrowest width, which truncate like the cells.',
    initialState: false
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
    help: 'Count is right-aligned as-is, text is left-aligned.',
    options: listOptions<RankedTableCellRender>({
      count: 'Count',
      text: 'Text'
    }),
    initialState: 'count' as const
  },
  fixedBarRange: {
    type: 'boolean' as const,
    title: 'Fixed bar range',
    help: 'Scales the bars against a fixed 0 - 1000 range, clamped to it, instead of against the largest value in the column.',
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
    help: 'Each cell carries its own bar `color`, overriding the default bar color.',
    initialState: false
  },
  linkedHosts: {
    type: 'boolean' as const,
    title: 'Linked host cells',
    help: 'Cells with an `href` render as links.',
    initialState: false
  }
} satisfies PanelConfigFor<typeof CmkRankedTable, 'rows' | 'columns'> & {
  containerHeight: NumberPropDef
  containerWidth: NumberPropDef
  longHostNames: BoolPropDef
  serviceColumn: BoolPropDef
  longColumnTitles: BoolPropDef
  rowCount: NumberPropDef
  valueBar: BoolPropDef
  valueRender: ListPropDef<RankedTableCellRender>
  fixedBarRange: BoolPropDef
  preFormatted: BoolPropDef
  perRowColor: BoolPropDef
  linkedHosts: BoolPropDef
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
  UclPropertiesPanel,
  UclResizablePreview
} from '@ucl/_ucl/components/detail-page'
import { computed } from 'vue'

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
  { host: '10.0.71.219', flows: 1284 },
  { host: '10.0.234.247', flows: 967 },
  { host: '10.0.171.51', flows: 411 },
  { host: '10.0.151.254', flows: 388 },
  { host: '10.0.198.27', flows: 154 },
  { host: '10.0.139.151', flows: 102 },
  { host: '10.0.104.62', flows: 97 },
  { host: '10.0.88.13', flows: 74 },
  { host: '10.0.57.201', flows: 61 },
  { host: '10.0.42.98', flows: 43 },
  { host: '10.0.31.7', flows: 28 },
  { host: '10.0.12.44', flows: 11 }
]

const LONG_HOST_NAMES = [
  'node_webshop_i-020818453318b7c7.eu-central-1.compute.internal',
  'fileserver-01.corp.meridian-retail.com',
  'web-frontend-01.corp.meridian-retail.com',
  'app-redis-02.corp.meridian-retail.com',
  'db-postgres-01.corp.meridian-retail.com',
  'node_lab_i-0179408522d484ce3.eu-central-1.compute.internal',
  'app-worker-02.corp.meridian-retail.com',
  'payment-api-02.corp.meridian-retail.com',
  'backup-01.corp.meridian-retail.com',
  'app-worker-01.corp.meridian-retail.com',
  'db-postgres-02.corp.meridian-retail.com',
  'localhost'
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
    title: propState.value.longColumnTitles ? 'Local host name' : 'Host',
    render: 'text',
    bar: false
  },
  ...(propState.value.serviceColumn
    ? [
        {
          key: 'service',
          title: propState.value.longColumnTitles ? 'Service description' : 'Service',
          render: 'text' as const,
          bar: false
        }
      ]
    : []),
  {
    key: 'flows',
    title: 'Flows',
    render: propState.value.valueRender,
    bar: propState.value.valueBar,
    ...(propState.value.fixedBarRange ? { barRange: [0, 1000] as [number, number] } : {})
  }
])

const rows = computed<RankedTableRow[]>(() =>
  HOSTS.slice(0, Math.max(0, propState.value.rowCount)).map((entry, index) => {
    const host = propState.value.longHostNames ? LONG_HOST_NAMES[index]! : entry.host
    return {
      host: propState.value.linkedHosts ? { value: host, href: '#' } : host,
      service: 'Interface 1',
      flows: {
        value: entry.flows,
        ...(propState.value.preFormatted ? { formatted: `${entry.flows} flows` } : {}),
        ...(propState.value.perRowColor ? { color: ROW_COLORS[index % ROW_COLORS.length]! } : {})
      }
    }
  })
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkRankedTable</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview
        v-model:width="propState.containerWidth"
        v-model:height="propState.containerHeight"
      >
        <CmkRankedTable :columns="columns" :rows="rows" />
      </UclResizablePreview>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
