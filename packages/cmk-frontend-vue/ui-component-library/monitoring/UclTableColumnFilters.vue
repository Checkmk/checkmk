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
      'Each filterable column header exposes a filter button after its label, reachable in the natural tab order with an accessible name of the form "Filter <column>". The button reports aria-haspopup / aria-expanded.'
  },
  {
    keys: ['↑', '↓', 'Home', 'End'],
    description:
      'While the dropdown is open, arrow keys move the active option (Home/End jump to first/last). The active option is tracked by the parent FilterDropdown and exposed via aria-activedescendant; the option rows only render the highlight.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Toggle the active option (or "Select all"). Space types normally while the search field is focused, so it is only treated as a toggle outside the input.'
  },
  {
    keys: ['Esc'],
    description:
      'Clears the search field if it has text, otherwise closes the dropdown and returns focus to the filter button.'
  }
]

export const panelConfig = {
  optionCount: {
    type: 'list' as const,
    title: 'State option count',
    options: [
      { name: 'few', title: 'Few (no search field)' },
      { name: 'many', title: 'Many (search field shown)' }
    ],
    initialState: 'few',
    help: 'The inline search field appears once the option count exceeds the dropdown threshold.'
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
import type { ColumnFilterNode, FilterField, HostEntry } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import type { CheckboxListFilter } from '@/monitoring/shared/components/filter/types'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const FEW_STATES = ['UP', 'DOWN', 'UNREACHABLE', 'PENDING']
const MANY_STATES = [
  ...FEW_STATES,
  'FLAPPING',
  'IN DOWNTIME',
  'ACKNOWLEDGED',
  'STALE',
  'NO NOTIFICATIONS',
  'NO CHECKS',
  'PASSIVE',
  'CLUSTERED'
]

const stateFilter = computed<CheckboxListFilter>(() => ({
  type: 'checkbox-list',
  field: 'state',
  options: (propState.value.optionCount === 'many' ? MANY_STATES : FEW_STATES).map((state) => ({
    value: state,
    title: state
  }))
}))

// Only the State column carries a filter dropdown in this demo; the remaining
// columns are non-filterable so the dropdown stays the focus of the example.
const columns = computed<ColumnDef<HostEntry>[]>(() => [
  {
    accessorKey: 'state',
    header: 'State',
    minSize: 60,
    maxSize: 130,
    meta: { filter: stateFilter.value }
  },
  { accessorKey: 'name', header: 'Host', minSize: 100, maxSize: 320, enableColumnFilter: false },
  { accessorKey: 'alias', header: 'Alias', minSize: 100, maxSize: 320, enableColumnFilter: false },
  { accessorKey: 'ip', header: 'IP address', minSize: 100, maxSize: 160, enableColumnFilter: false }
])

const filterState = ref<ColumnFiltersState>([])

const activeFilters = computed(() =>
  filterState.value.map((entry) => {
    const node = entry.value as ColumnFilterNode<FilterField>
    const values =
      node && 'value' in node && Array.isArray(node.value)
        ? (node.value as string[]).join(', ')
        : ''
    return `${entry.id}: ${values}`
  })
)

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
        <!--
          The table scrolls its own overflow, so the open dropdown needs vertical
          room inside the table box; give the viewport enough height that the
          popover is not clipped in this demo.
        -->
        <div class="ucl-table-column-filters__viewport">
          <MonitoringTable
            :rows="rows"
            :loading="false"
            :columns="columns"
            :sort-state="[]"
            :filter-state="filterState"
            :get-row-key="(row) => `${row.site_id}/${row.name}`"
            @update:filter-state="filterState = $event"
          >
            <template #row="{ row }">
              <HostRow :row="row" />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-table-column-filters__readout">
          Active filters:
          <code v-if="activeFilters.length">{{ activeFilters.join(' · ') }}</code>
          <span v-else>none</span>
        </p>

        <p class="ucl-table-column-filters__hint">
          The State column declares a <code>checkbox-list</code> filter via
          <code>meta.filter</code>. The header button opens the FilterDropdown, which owns the
          popover and all keyboard handling; the checkbox list only renders the active row. Selected
          values persist in the table's column-filter state, so they survive closing the dropdown
          and drive the (server-side) query. Future filter types — numeric range, IP range — plug in
          as additional dropdown contents without changing this wiring.
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

.ucl-table-column-filters__viewport {
  /* The table clips its own overflow, so a definite height (not min-height) is
     needed for the table's height:100% to resolve and leave room for the open
     dropdown below the header. */
  width: 100%;
  height: 420px;
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
