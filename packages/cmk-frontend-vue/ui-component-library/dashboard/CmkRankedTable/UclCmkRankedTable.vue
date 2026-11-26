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

type TableState = 'data' | 'refreshing' | 'loading' | 'empty' | 'error'

export const panelConfig = {
  tableState: {
    type: 'list' as const,
    title: 'State',
    help: 'How the table looks while its data loads, refreshes, comes back empty or fails. The error state is the widget alert that replaces the table.',
    options: listOptions<TableState>({
      data: 'Data',
      refreshing: 'Refreshing (aria-busy)',
      loading: 'Loading',
      empty: 'Empty',
      error: 'Error'
    }),
    initialState: 'data' as const
  },
  lastSuccessMinutes: {
    type: 'number' as const,
    title: 'Last success (min ago)',
    help: 'Error state only. 0 means no fetch has succeeded yet, so the server detail is shown.',
    initialState: 5
  },
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
  label: {
    type: 'string' as const,
    title: 'Label',
    help: 'Accessible name of the table, e.g. the widget title.',
    initialState: 'Top 6: Flows'
  },
  showRank: {
    type: 'boolean' as const,
    title: 'Show rank',
    help: "Prepends each row's position, starting at 1.",
    initialState: true
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
    help: 'Adds a second text column, in the quieter secondary tone.',
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
  units: {
    type: 'boolean' as const,
    title: 'Units',
    help: 'Gives each value a `unit`, shown quietly after it.',
    initialState: true
  },
  zeroAndTinyValues: {
    type: 'boolean' as const,
    title: 'Zero and tiny values',
    help: 'Ends the table with a value of 0, which has an empty bar, and a tiny one, whose bar keeps a sliver.',
    initialState: false
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
} satisfies PanelConfigFor<
  typeof CmkRankedTable,
  'rows' | 'columns' | 'placeholder' | 'busy' | 'rowKey'
> & {
  units: BoolPropDef
  zeroAndTinyValues: BoolPropDef
  tableState: ListPropDef<TableState>
  lastSuccessMinutes: NumberPropDef
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
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { computed, ref } from 'vue'

import CmkRankedTable, {
  type RankedTableColumn,
  type RankedTablePlaceholder,
  type RankedTableRow
} from '@/dashboard/components/CmkRankedTable'
import WidgetDataErrorAlert from '@/dashboard/components/DashboardContent/figures/WidgetDataErrorAlert.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkRankedTable,
  'rows' | 'columns' | 'placeholder' | 'busy' | 'rowKey'
>().createRef(panelConfig)

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
          bar: false,
          tone: 'secondary' as const
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

const placeholder = computed<RankedTablePlaceholder | undefined>(() => {
  const kind = propState.value.tableState
  return kind === 'loading' || kind === 'empty'
    ? { kind, rows: Math.max(1, propState.value.rowCount) }
    : undefined
})

const lastSuccessAt = computed(() =>
  propState.value.lastSuccessMinutes > 0
    ? Date.now() - propState.value.lastSuccessMinutes * 60_000
    : undefined
)

const ZERO_AND_TINY = [
  { host: '10.0.9.18', flows: 2 },
  { host: '10.0.9.7', flows: 0 }
]

// Each refresh scales every value by its own factor and ranks the rows anew.
const refreshes = ref(0)

function refreshed(entries: typeof HOSTS): typeof HOSTS {
  if (refreshes.value === 0) {
    return entries
  }
  return entries
    .map((entry, index) => ({
      ...entry,
      flows: Math.round(entry.flows * (0.4 + (((index + refreshes.value) * 7) % 13) / 10))
    }))
    .sort((a, b) => b.flows - a.flows)
}

function hostOf(row: RankedTableRow): string {
  const host = row.host!
  return String(typeof host === 'object' ? host.value : host)
}

const rows = computed<RankedTableRow[]>(() => {
  const ranked = HOSTS.slice(0, Math.max(0, propState.value.rowCount))
  const named = [...ranked, ...(propState.value.zeroAndTinyValues ? ZERO_AND_TINY : [])].map(
    (entry, index) => ({
      ...entry,
      host: propState.value.longHostNames ? (LONG_HOST_NAMES[index] ?? entry.host) : entry.host
    })
  )
  return [...refreshed(named.slice(0, ranked.length)), ...named.slice(ranked.length)].map(
    (entry, index) => ({
      host: propState.value.linkedHosts ? { value: entry.host, href: '#' } : entry.host,
      service: 'Interface 1',
      flows: {
        value: entry.flows,
        ...(propState.value.preFormatted ? { formatted: `${entry.flows} flows` } : {}),
        ...(propState.value.units ? { unit: 'flows/s' } : {}),
        ...(propState.value.perRowColor ? { color: ROW_COLORS[index % ROW_COLORS.length]! } : {})
      }
    })
  )
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkRankedTable</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview
        v-model:width="propState.containerWidth"
        v-model:height="propState.containerHeight"
      >
        <WidgetDataErrorAlert
          v-if="propState.tableState === 'error'"
          detail="Monitoring data source unavailable"
          :last-success-at="lastSuccessAt"
        />
        <CmkRankedTable
          v-else
          :columns="columns"
          :rows="rows"
          :placeholder="placeholder"
          :busy="propState.tableState === 'refreshing'"
          :show-rank="propState.showRank"
          :label="propState.label"
          :row-key="hostOf"
        >
          <template #empty>
            <CmkHeading type="h4">No data</CmkHeading>
            <CmkParagraph
              >Nothing matches the widget filter in the selected time frame.</CmkParagraph
            >
          </template>
        </CmkRankedTable>
      </UclResizablePreview>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
        <div class="ucl-cmk-ranked-table__refresh">
          <CmkButton @click="refreshes += 1">Refresh data</CmkButton>
          <CmkParagraph>New values and a new ranking, to see the refresh animation.</CmkParagraph>
        </div>
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-ranked-table__refresh {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--dimension-3);
  margin-top: var(--dimension-6);
}
</style>
