<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclTableColumnFilters.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Each filterable column header exposes a filter button after its label. It is a regular button, reachable in the natural tab order, and carries an accessible name of the form "Filter <column>".'
  },
  {
    keys: ['—'],
    description:
      'The button is presentational for now. The dropdown it will open and its keyboard interaction (open/close, option navigation, expanded-state announcement) are handled in the follow-up FilterDropdown ticket (CMK-35454).'
  }
]

export const panelConfig = {
  textColumnsOnly: {
    type: 'boolean' as const,
    title: 'Only text columns filterable',
    initialState: true,
    help: 'When enabled, only the text columns expose a filter button. Disable to make every column filterable (getCanFilter()).'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import { type ColumnDef, type ColumnFiltersState } from '@tanstack/vue-table'
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

const TEXT_COLUMNS = new Set(['name', 'alias', 'ip'])

const columns = computed<ColumnDef<HostEntry>[]>(() => {
  const textOnly = propState.value.textColumnsOnly
  const filterable = (id: string): boolean => !textOnly || TEXT_COLUMNS.has(id)
  return [
    { accessorKey: 'state', header: 'State', minSize: 60, maxSize: 130, enableColumnFilter: false },
    { accessorKey: 'name', header: 'Host', minSize: 100, maxSize: 320 },
    { accessorKey: 'alias', header: 'Alias', minSize: 100, maxSize: 320 },
    { accessorKey: 'ip', header: 'IP address', minSize: 100, maxSize: 160 },
    {
      accessorKey: 'num_services_ok',
      header: 'OK',
      meta: { justify: 'center' },
      minSize: 64,
      maxSize: 90,
      enableColumnFilter: filterable('num_services_ok')
    },
    {
      accessorKey: 'num_services_warn',
      header: 'Warn',
      meta: { justify: 'center' },
      minSize: 64,
      maxSize: 90,
      enableColumnFilter: filterable('num_services_warn')
    },
    {
      accessorKey: 'num_services_crit',
      header: 'Crit',
      meta: { justify: 'center' },
      minSize: 64,
      maxSize: 90,
      enableColumnFilter: filterable('num_services_crit')
    }
  ]
})

const filterState = ref<ColumnFiltersState>([{ id: 'name', value: 'demo' }])

const activeFilters = computed(() => filterState.value.map((entry) => entry.id))

const rows: HostEntry[] = [
  {
    name: 'web-server-01',
    state: 'UP',
    ip: '10.0.0.1',
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
    ip: '10.0.0.27',
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
    ip: '10.0.0.51',
    alias: 'Redis cache node',
    site_id: 'local',
    num_services: 12,
    num_services_ok: 12,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0
  }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Table column filters</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-table-column-filters__stack">
        <MonitoringTable
          :rows="rows"
          :loading="false"
          :columns="columns"
          :sort-state="[]"
          :filter-state="filterState"
          :get-row-key="(row) => `${row.site_id}/${row.name}`"
        >
          <template #row="{ row }">
            <HostRow :row="row" />
          </template>
        </MonitoringTable>

        <p class="ucl-table-column-filters__readout">
          Active filters:
          <code v-if="activeFilters.length">{{ activeFilters.join(', ') }}</code>
          <span v-else>none</span>
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
.ucl-table-column-filters__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
  margin-left: calc(-1 * var(--dimension-10));
}

.ucl-table-column-filters__readout {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}

.ucl-table-column-filters__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
