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
      'While the dropdown is open, arrow keys move the active option (Home/End jump to first/last). The active option is tracked by the parent FilterDropdown and exposed via aria-activedescendant; the option rows only render the highlight. Exception: a numeric or date-time-range filter leaves its arrow keys to the input itself, since those step the value natively.'
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
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState
} from '@tanstack/vue-table'
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import { computed, provide, ref } from 'vue'

import HostRow from '@/monitoring/all-hosts/components/HostRow.vue'
import type { ColumnFilterNode, FilterField, HostEntry } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type {
  BooleanGroupFilter,
  CheckboxListWithFlagsFilter,
  DateTimeRangeFilter,
  NumericFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'
import { FILLED_MODE_COLUMN_WIDTH, MODE_COLUMN_ID } from '@/monitoring/shared/components/modeColumn'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

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

const stateFilter = computed<CheckboxListWithFlagsFilter>(() => ({
  type: 'checkbox-list-with-flags',
  field: 'state',
  options: (propState.value.optionCount === 'many' ? MANY_STATES : FEW_STATES).map((state) => ({
    value: state,
    title: state
  })),
  flags: [
    { field: 'is_flapping', title: 'Flapping' },
    { field: 'stale', title: 'Stale' }
  ]
}))
const modesFilter = computed<BooleanGroupFilter>(() => ({
  type: 'boolean-group',
  groups: [
    { field: 'in_downtime', title: 'In downtime' },
    { field: 'acknowledged', title: 'Acknowledged' },
    { field: 'notifications_enabled', title: 'Notifications enabled' }
  ]
}))

const nameFilter = computed<StringInputFilter>(() => ({
  type: 'string-input',
  field: 'name'
}))

const aliasFilter = computed<StringInputFilter>(() => ({
  type: 'string-input',
  field: 'alias'
}))

const addressFilter = computed<StringInputFilter>(() => ({
  type: 'string-input',
  field: 'address'
}))

const DEMO_LABELS = [
  'cmk/check_mk_server:yes',
  'cmk/docker_object:container',
  'cmk/docker_object:node',
  'cmk/os_family:linux',
  'cmk/os_family:windows',
  'cmk/site:heute',
  'criticality:prod',
  'criticality:test',
  'networking:core',
  'networking:edge'
]

function suggestLabels(query: string): Promise<string[]> {
  const needle = query.trim().toLowerCase()
  return Promise.resolve(DEMO_LABELS.filter((label) => label.toLowerCase().includes(needle)))
}

const labelsFilter = computed<StringInputFilter>(() => ({
  type: 'string-input',
  field: 'name',
  suggest: suggestLabels,
  keyValue: true,
  wildcardOption: true
}))

const servicesFilter = computed<NumericFilter>(() => ({
  type: 'numeric',
  field: 'num_services'
}))

const lastCheckFilter = computed<DateTimeRangeFilter>(() => ({
  type: 'date-time-range',
  field: 'last_check'
}))

const columns = computed<ColumnDef<HostEntry>[]>(() => [
  {
    accessorKey: 'state',
    header: 'State',
    minSize: 60,
    maxSize: 130,
    meta: { filter: stateFilter.value }
  },
  {
    accessorKey: MODE_COLUMN_ID,
    header: 'Mode',
    enableSorting: false,
    minSize: FILLED_MODE_COLUMN_WIDTH,
    maxSize: FILLED_MODE_COLUMN_WIDTH,
    meta: { justify: 'left', filter: modesFilter.value }
  },
  {
    accessorKey: 'name',
    header: 'Host',
    minSize: 100,
    maxSize: 320,
    meta: { filter: nameFilter.value }
  },
  {
    accessorKey: 'alias',
    header: 'Alias',
    minSize: 100,
    maxSize: 320,
    meta: { filter: aliasFilter.value }
  },
  {
    accessorKey: 'address',
    header: 'IP address',
    minSize: 100,
    maxSize: 160,
    meta: { filter: addressFilter.value }
  },
  {
    accessorKey: 'num_services',
    header: 'Services',
    minSize: 80,
    maxSize: 120,
    meta: { filter: servicesFilter.value }
  },
  {
    accessorKey: 'last_check',
    header: 'Last check',
    sortDescFirst: true,
    minSize: 120,
    maxSize: 200,
    meta: { filter: lastCheckFilter.value }
  },
  {
    accessorKey: 'labels',
    header: 'Labels',
    enableSorting: false,
    minSize: 160,
    maxSize: 320,
    meta: { filter: labelsFilter.value }
  }
])

const filterState = ref<ColumnFiltersState>([])

const sortState = ref<SortingState>([])

const demoService = {
  sortState,
  columnVisibility: ref<VisibilityState>({}),
  rowToReveal: ref<string | null>(null),
  updateSort(next: SortingState) {
    sortState.value = next
  },
  beginAutoPause() {},
  endAutoPause() {}
}

provide(MONITORING_SERVICE, demoService as unknown as MonitoringService<unknown>)

function describeNode(node: ColumnFilterNode<FilterField>): string {
  if (node.type === 'and') {
    return node.children.map(describeNode).join(' and ')
  }
  if (node.type === 'or') {
    return node.children.map(describeNode).join(' or ')
  }
  if (node.type === 'condition') {
    const value = Array.isArray(node.value) ? node.value.join(', ') : String(node.value)
    return `${node.op} ${value}`
  }
  return ''
}

const activeFilters = computed(() =>
  filterState.value.map((entry) => {
    const node = entry.value as ColumnFilterNode<FilterField>
    return `${entry.id}: ${node ? describeNode(node) : ''}`
  })
)

const rows: HostEntry[] = [
  {
    name: 'web-server-01',
    modes: [
      {
        icon_name: 'downtime',
        link: 'view.py?view_name=downtimes_of_host&host=web-server-01',
        title: 'In scheduled downtime'
      }
    ],
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.1',
    alias: 'Frontend web server (eu-west)',
    site_id: 'local',
    num_services: 48,
    num_services_ok: 42,
    num_services_warn: 3,
    num_services_crit: 1,
    num_services_unknown: 0,
    num_services_pending: 2,
    labels: {
      'cmk/os_family': { source: 'discovered', value: 'linux' },
      criticality: { source: 'explicit', value: 'prod' }
    },
    last_check: 1789625643,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-server-01',
    num_relations: 0
  },
  {
    name: 'db-primary-02',
    modes: [
      {
        icon_name: 'ack',
        link: 'view.py?view_name=hostproblems&host=db-primary-02',
        title: 'Problem acknowledged'
      },
      {
        icon_name: 'notif_disabled',
        link: 'view.py?view_name=hoststatus&host=db-primary-02',
        title: 'Notifications disabled'
      }
    ],
    state: 'DOWN',
    is_flapping: false,
    stale: false,
    address: '10.0.0.27',
    alias: 'Primary database (eu-west)',
    site_id: 'local',
    num_services: 31,
    num_services_ok: 18,
    num_services_warn: 4,
    num_services_crit: 7,
    num_services_unknown: 1,
    num_services_pending: 1,
    labels: {
      'cmk/os_family': { source: 'discovered', value: 'linux' },
      criticality: { source: 'explicit', value: 'prod' }
    },
    last_check: 1789624361,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=db-primary-02',
    num_relations: 0
  },
  {
    name: 'cache-node-03',
    modes: [],
    state: 'UP',
    is_flapping: false,
    stale: false,
    address: '10.0.0.51',
    alias: 'Redis cache node',
    site_id: 'local',
    num_services: 12,
    num_services_ok: 12,
    num_services_warn: 0,
    num_services_crit: 0,
    num_services_unknown: 0,
    num_services_pending: 0,
    labels: {
      'cmk/os_family': { source: 'discovered', value: 'linux' },
      criticality: { source: 'explicit', value: 'test' }
    },
    last_check: 1789592712,
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=cache-node-03',
    num_relations: 0
  }
]

function compareValues(left: unknown, right: unknown): number {
  if (left === undefined) {
    return right === undefined ? 0 : -1
  }
  if (right === undefined) {
    return 1
  }
  if (typeof left === 'number' && typeof right === 'number') {
    return left - right
  }
  return String(left).localeCompare(String(right))
}

const sortedRows = computed<HostEntry[]>(() => {
  if (sortState.value.length === 0) {
    return rows
  }
  return [...rows].sort((left, right) => {
    for (const entry of sortState.value) {
      const order = compareValues(
        left[entry.id as keyof HostEntry],
        right[entry.id as keyof HostEntry]
      )
      if (order !== 0) {
        return entry.desc ? -order : order
      }
    }
    return 0
  })
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Table column filters</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-table-column-filters__stack">
        <div class="ucl-table-column-filters__viewport">
          <MonitoringTable
            :rows="sortedRows"
            :fetch-state="'idle'"
            :has-loaded="true"
            :columns="columns"
            :filter-state="filterState"
            :get-row-key="(row) => `${row.site_id}/${row.name}`"
            @update:filter-state="filterState = $event"
          >
            <template #row="{ row, tableRow }">
              <HostRow :row="row" :table-row="tableRow" />
            </template>
          </MonitoringTable>
        </div>

        <p class="ucl-table-column-filters__readout">
          Active filters:
          <code v-if="activeFilters.length">{{ activeFilters.join(' · ') }}</code>
          <span v-else>none</span>
        </p>

        <p class="ucl-table-column-filters__hint">
          The State column declares a <code>checkbox-list-with-flags</code> filter via
          <code>meta.filter</code>: the state options plus the orthogonal flapping/stale flags,
          which are AND-combined with the list's own condition. The header button opens the
          FilterDropdown, which owns the popover and all keyboard handling; the checkbox list only
          renders the active row. Selected values persist in the table's column-filter state, so
          they survive closing the dropdown and drive the (server-side) query. Future filter types —
          numeric range, IP range — plug in as additional dropdown contents without changing this
          wiring. The Mode column declares a <code>boolean-group</code> filter: one tri-state group
          per boolean field, whose non-"Any" groups are AND-combined into the node. The Labels
          column shows the same <code>string-input</code> type with a <code>suggest</code> callback,
          which swaps its plain text field for a CmkChipAutocomplete: several picks become an
          <code>or</code> of one <code>contains</code> each. It targets the host name here because
          the API carries no label condition yet; the column filter itself needs no change once it
          does.
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
  display: flex;
  flex-direction: column;
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
