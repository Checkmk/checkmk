<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclColumnPinning.vue?raw'

export const a11yData = [
  {
    keys: ['—'],
    description:
      'Pinning is purely presentational: it adds sticky positioning to the leading and trailing columns. The table keeps its normal reading order and keyboard semantics; nothing is added to or removed from the tab order.'
  }
]

export const panelConfig = {
  pinnedColumns: {
    type: 'number' as const,
    title: 'Pinned columns',
    initialState: 2,
    help: 'Number of leading columns pinned to the left edge while scrolling horizontally.'
  },
  rightPinnedColumns: {
    type: 'number' as const,
    title: 'Right-pinned columns',
    initialState: 1,
    help: 'Number of trailing columns pinned to the right edge while scrolling horizontally.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import { type ColumnDef, type ColumnPinningState } from '@tanstack/vue-table'
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, ref } from 'vue'

import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import type { HostEntry } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const columns: ColumnDef<HostEntry>[] = [
  { accessorKey: 'state', header: 'State', minSize: 60, maxSize: 130 },
  { accessorKey: 'name', header: 'Host', minSize: 100, maxSize: 320 },
  { accessorKey: 'alias', header: 'Alias', minSize: 100, maxSize: 320 },
  { accessorKey: 'address', header: 'IP address', minSize: 100, maxSize: 160 },
  {
    accessorKey: 'num_services_ok',
    header: 'OK',
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_warn',
    header: 'Warn',
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_crit',
    header: 'Crit',
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_unknown',
    header: 'Unknown',
    meta: { justify: 'center' },
    minSize: 92,
    maxSize: 130
  },
  {
    accessorKey: 'num_services_pending',
    header: 'Pending',
    meta: { justify: 'center' },
    minSize: 92,
    maxSize: 120
  }
]

const totalMinWidth = columns.reduce((sum, column) => sum + (column.minSize ?? 0), 0)

const maxPinnable = columns.length - 1

const pinnedColumns = computed(() =>
  Math.max(0, Math.min(propState.value.pinnedColumns, maxPinnable))
)

const rightPinnedColumns = computed(() =>
  Math.max(0, Math.min(propState.value.rightPinnedColumns, maxPinnable - pinnedColumns.value))
)

const accessorKeys = columns.map((column) => (column as { accessorKey: string }).accessorKey)

const columnPinning = computed<ColumnPinningState>(() => ({
  left: accessorKeys.slice(0, pinnedColumns.value),
  right: rightPinnedColumns.value > 0 ? accessorKeys.slice(-rightPinnedColumns.value) : []
}))

const rows: HostEntry[] = [
  {
    name: 'web-server-01',
    state: 'UP',
    address: '10.0.0.1',
    alias: 'Frontend web server (eu-west)',
    site_id: 'local',
    num_services: 48,
    num_services_ok: 42,
    num_services_warn: 3,
    num_services_crit: 1,
    num_services_unknown: 0,
    num_services_pending: 2
  },
  {
    name: 'db-primary-02',
    state: 'DOWN',
    address: '10.0.0.27',
    alias: 'Primary database (eu-west)',
    site_id: 'local',
    num_services: 31,
    num_services_ok: 18,
    num_services_warn: 4,
    num_services_crit: 7,
    num_services_unknown: 1,
    num_services_pending: 1
  },
  {
    name: 'cache-node-03',
    state: 'UP',
    address: '10.0.0.51',
    alias: 'Redis cache node',
    site_id: 'local',
    num_services: 12,
    num_services_ok: 12,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0
  },
  {
    name: 'mail-relay-04',
    state: 'UNREACHABLE',
    address: '10.0.0.88',
    alias: 'Outbound mail relay',
    site_id: 'local',
    num_services: 19,
    num_services_ok: 15,
    num_services_warn: 2,
    num_services_crit: 0,
    num_services_unknown: 2,
    num_services_pending: 0
  }
]

const SLIDER_MIN = 280
const SLIDER_MAX = 1100
const containerWidth = ref<number>(520)

const sliderFillPercent = computed(() => {
  const range = SLIDER_MAX - SLIDER_MIN
  return range <= 0 ? 0 : ((containerWidth.value - SLIDER_MIN) / range) * 100
})

const sliderTrackBackground = computed(
  () =>
    `linear-gradient(to right, var(--success) 0%, var(--success) ${sliderFillPercent.value}%, var(--ux-theme-6) ${sliderFillPercent.value}%, var(--ux-theme-6) 100%)`
)

const pinningActive = computed(
  () => pinnedColumns.value > 0 && containerWidth.value < totalMinWidth
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Table column pinning</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-column-pinning__stack">
        <div class="ucl-column-pinning__controls">
          <div
            class="ucl-column-pinning__controls-header"
            :style="{ width: `${containerWidth}px` }"
          >
            <span class="ucl-column-pinning__label">Container width</span>
            <span class="ucl-column-pinning__readout">
              <strong>{{ containerWidth }} px</strong>
              <span>
                · total min width <code>{{ totalMinWidth }} px</code> ·
                <code>{{ pinningActive ? 'pinned' : 'not pinned' }}</code>
              </span>
            </span>
          </div>
          <input
            v-model.number="containerWidth"
            type="range"
            :min="SLIDER_MIN"
            :max="SLIDER_MAX"
            :style="{ width: `${SLIDER_MAX}px`, background: sliderTrackBackground }"
            class="ucl-column-pinning__slider"
          />
        </div>

        <div class="ucl-column-pinning__viewport" :style="{ width: `${containerWidth}px` }">
          <MonitoringTable
            :rows="rows"
            :fetch-state="'idle'"
            :has-loaded="true"
            :columns="columns"
            :sort-state="[]"
            :filter-state="[]"
            :column-pinning="columnPinning"
            :get-row-key="(row) => `${row.site_id}/${row.name}`"
          >
            <template #row="{ row, tableRow }">
              <HostRow :row="row" :table-row="tableRow" />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-column-pinning__hint">
          Drag the slider to narrow the container. Columns first shrink towards their min size; once
          every column has reached its min size and the table can no longer fit, the leading
          {{ pinnedColumns }} column(s) stay pinned to the left and the trailing
          {{ rightPinnedColumns }} column(s) stay pinned to the right while the rest scroll.
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-column-pinning__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
  margin-left: calc(-1 * var(--dimension-10));
}

.ucl-column-pinning__controls {
  max-width: 100%;
}

.ucl-column-pinning__controls-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--dimension-2);
  margin-bottom: var(--dimension-2);
}

.ucl-column-pinning__label {
  font-weight: var(--font-weight-bold);
}

.ucl-column-pinning__readout {
  font-style: italic;
  opacity: 0.7;
}

.ucl-column-pinning__slider {
  appearance: none;
  display: block;
  height: 6px;
  margin: var(--dimension-4) 0 0;
  padding: 0;
  background: var(--ux-theme-6);
  border-radius: 3px;
  cursor: pointer;
}

.ucl-column-pinning__slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-column-pinning__slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--success);
  border: none;
  cursor: pointer;
}

.ucl-column-pinning__viewport {
  box-sizing: content-box;
  max-width: 100%;
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
}

.ucl-column-pinning__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
