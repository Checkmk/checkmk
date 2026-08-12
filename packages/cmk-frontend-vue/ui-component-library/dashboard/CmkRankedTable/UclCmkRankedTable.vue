<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import { type ChartColor } from '@/dashboard/components/CmkRankedTable'

import codeExample from './UclCmkRankedTableCodeExample.vue?raw'

export const panelConfig = {
  barColor: {
    type: 'list' as const,
    title: 'Bar color',
    options: [
      { title: 'Blue', name: 'blue' },
      { title: 'Green', name: 'green' },
      { title: 'Grey', name: 'grey' },
      { title: 'Magenta', name: 'magenta' },
      { title: 'Orange', name: 'orange' },
      { title: 'Purple', name: 'purple' },
      { title: 'Red', name: 'red' },
      { title: 'Yellow', name: 'yellow' }
    ] satisfies Options<ChartColor>[],
    initialState: 'green' as const
  }
} satisfies PanelConfigFor<typeof CmkRankedTable, 'rows' | 'columns'>
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

import CmkRankedTable, {
  type RankedTableColumn,
  type RankedTableRow
} from '@/dashboard/components/CmkRankedTable'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkRankedTable, 'rows' | 'columns'>().createRef(
  panelConfig
)

const columns: RankedTableColumn[] = [
  { key: 'host', title: 'Host', render: 'text', bar: false },
  { key: 'volume', title: 'Volume', render: 'bytes', bar: true },
  { key: 'flows', title: 'Flows', render: 'count', bar: false }
]

// Rows are provided pre-ranked; the bar scales relative to the largest value.
const rows: RankedTableRow[] = [
  { host: '10.0.71.219', volume: 194_420_000_000, flows: 1284 },
  { host: '10.0.234.247', volume: 158_270_000_000, flows: 967 },
  { host: '10.0.171.51', volume: 58_270_000_000, flows: 411 },
  { host: '10.0.151.254', volume: 51_670_000_000, flows: 388 },
  { host: '10.0.198.27', volume: 27_380_000_000, flows: 154 },
  { host: '10.0.139.151', volume: 22_260_000_000, flows: 102 }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkRankedTable</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkRankedTable :columns="columns" :rows="rows" :bar-color="propState.barColor" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
