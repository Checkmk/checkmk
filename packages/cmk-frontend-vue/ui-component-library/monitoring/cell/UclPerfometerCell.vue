<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclPerfometerCellCodeExample.vue?raw'

export const panelConfig = {
  value: {
    type: 'number' as const,
    title: 'value',
    initialState: 65,
    help: 'Current metric value, positioned within value_range to derive the fill level.'
  },
  min: {
    type: 'number' as const,
    title: 'min',
    initialState: 0,
    help: 'Lower bound of the value range.'
  },
  max: {
    type: 'number' as const,
    title: 'max',
    initialState: 100,
    help: 'Upper bound of the value range.'
  },
  formatted: {
    type: 'string' as const,
    title: 'formatted',
    initialState: '65.0%',
    help: 'Text overlaid on top of the bar (the formatted metric value).'
  },
  color: {
    type: 'list' as const,
    title: 'color',
    options: [
      { title: 'green', name: '#13d389' },
      { title: 'yellow', name: '#ffd000' },
      { title: 'red', name: '#ff5769' },
      { title: 'blue', name: '#3cc2ff' }
    ],
    initialState: '#13d389',
    help: 'Fill color of the bar.'
  },
  stale: {
    type: 'boolean' as const,
    title: 'stale',
    initialState: false,
    help: 'Desaturate the bar to indicate a stale check result.'
  },
  linked: {
    type: 'boolean' as const,
    title: 'linked',
    initialState: false,
    help: 'Wrap the cell in a link to the service graph.'
  },
  minWidth: {
    type: 'number' as const,
    title: 'minWidth',
    initialState: 170,
    help: 'Minimum column width in px (tanstack column minSize).'
  },
  maxWidth: {
    type: 'number' as const,
    title: 'maxWidth',
    initialState: 220,
    help: 'Maximum column width in px (tanstack column maxSize).'
  },
  justify: {
    type: 'list' as const,
    title: 'justify',
    options: [
      { title: 'left', name: 'left' },
      { title: 'center', name: 'center' },
      { title: 'right', name: 'right' }
    ],
    initialState: 'left',
    help: 'Horizontal alignment of the cell content.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import type { ColumnDef, ColumnFiltersState, SortingState } from '@tanstack/vue-table'
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import type { Perfometer } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { ColumnJustify } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellLink } from '@/monitoring/shared/components/cell/BaseCell.vue'
import PerfometerCell from '@/monitoring/shared/components/cell/PerfometerCell.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const data = computed<Perfometer>(() => ({
  value: propState.value.value,
  value_range: { min: propState.value.min, max: propState.value.max },
  formatted: propState.value.formatted,
  color: propState.value.color
}))

const linkedTo = computed<CellLink | undefined>(() =>
  propState.value.linked
    ? { href: 'graph.py?host=web-server-01&service=CPU%20load', target: '_top' }
    : undefined
)

const justify = computed<ColumnJustify>(() => propState.value.justify as ColumnJustify)

type DemoRow = { id: string }

const rows: DemoRow[] = [{ id: 'demo' }]
const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

const columns = computed<ColumnDef<DemoRow>[]>(() => [
  {
    id: 'cell',
    header: 'Perf-O-Meter',
    minSize: propState.value.minWidth,
    maxSize: propState.value.maxWidth,
    meta: { justify: justify.value }
  }
])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>PerfometerCell</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-perfometer-cell__table-wrap">
        <MonitoringTable
          :rows="rows"
          :fetch-state="'idle'"
          :has-loaded="true"
          :columns="columns"
          :sort-state="sortState"
          :filter-state="filterState"
          @update:sort-state="sortState = $event"
          @update:filter-state="filterState = $event"
        >
          <template #row>
            <PerfometerCell
              column-id="cell"
              :data="data"
              :stale="propState.stale"
              :linked-to="linkedTo"
            />
          </template>
        </MonitoringTable>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-perfometer-cell__table-wrap {
  width: 320px;
}
</style>
