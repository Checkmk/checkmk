<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ColumnDef, type ColumnPinningState } from '@tanstack/vue-table'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { onBeforeUnmount, onMounted, provide, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import { getKeyShortcutServiceInstance } from '@/lib/keyShortcuts'

import CmkSearchInput from '@/components/CmkSearchInput.vue'

import type { HostEntry, HostState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import type {
  CheckboxListFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringResultsCount from '../shared/components/MonitoringResultsCount.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import RefreshCountdown from '../shared/components/RefreshCountdown.vue'
import { HostApi } from './api/hosts'
import HostRow from './components/HostRow.vue'
import { HostService } from './services/HostService'

const { _t } = usei18n()

const props = defineProps<MonitoringAllHostsApp>()

const stateFilter: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: _t('UP') },
    { value: 'DOWN', title: _t('DOWN') },
    { value: 'UNREACHABLE', title: _t('UNREACH') }
  ] satisfies { value: HostState; title: string }[]
}

const nameFilter: StringInputFilter<'name'> = {
  type: 'string-input',
  field: 'name'
}

const aliasFilter: StringInputFilter<'alias'> = {
  type: 'string-input',
  field: 'alias'
}

const addressFilter: StringInputFilter<'address'> = {
  type: 'string-input',
  field: 'address'
}

const columns: ColumnDef<HostEntry>[] = [
  {
    id: 'select',
    header: '',
    enableSorting: false,
    minSize: 36,
    maxSize: 36,
    meta: { selectColumn: true, justify: 'center' }
  },
  {
    accessorKey: 'state',
    header: _t('State'),
    sortDescFirst: true,
    minSize: 60,
    maxSize: 130,
    meta: { filter: stateFilter }
  },
  {
    accessorKey: 'name',
    header: _t('Host'),
    sortDescFirst: false,
    minSize: 150,
    meta: { filter: nameFilter }
  },
  {
    accessorKey: 'alias',
    header: _t('Alias'),
    sortDescFirst: false,
    minSize: 150,
    meta: { filter: aliasFilter }
  },
  {
    accessorKey: 'address',
    header: _t('IP address'),
    sortDescFirst: false,
    minSize: 100,
    meta: { filter: addressFilter }
  },
  {
    accessorKey: 'num_services',
    header: _t('Total'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_ok',
    header: _t('OK'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_warn',
    header: _t('Wa'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_crit',
    header: _t('Cr'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_unknown',
    header: _t('Un'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_pending',
    header: _t('Pd'),
    sortDescFirst: true,
    meta: { justify: 'right' },
    minSize: 64,
    maxSize: 90
  }
]

const columnPinning: ColumnPinningState = { left: ['select', 'state', 'name'] }

const hostService = new HostService(new HostApi(), getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms,
  columns,
  quickFilters: [
    {
      label: _t('Unhandled Problems'),
      filter: {
        type: 'and',
        children: [
          {
            type: 'condition',
            field: 'state',
            op: 'one_of',
            value: ['DOWN', 'UNREACHABLE'] as HostState[]
          },
          { type: 'condition', field: 'acknowledged', op: 'eq', value: false }
        ]
      }
    }
  ]
})

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

onMounted(() => {
  hostService.onFocusSearch(() => searchInput.value?.focus())
})

onBeforeUnmount(() => {
  hostService.destruct()
})

provide(MONITORING_SERVICE, hostService)

function rowKey(row: HostEntry): string {
  return `${row.site_id}/${row.name}`
}
</script>

<template>
  <div class="monitoring-all-hosts-app">
    <div class="monitoring-all-hosts-app__header">
      <div class="monitoring-all-hosts-app__toolbar">
        <CmkSearchInput
          ref="searchInput"
          v-model="hostService.searchQuery.value"
          class="monitoring-all-hosts-app__search"
          :placeholder="_t('Search hosts…')"
          @search="hostService.updateSearch($event)"
          @focusin="hostService.beginAutoPause()"
          @focusout="hostService.endAutoPause()"
        />
        <div class="monitoring-all-hosts-app__quick-filters">
          <QuickFilterChip
            v-for="chip in hostService.filters.chips"
            :key="chip.label"
            :label="chip.label"
            :active="chip.isActive.value"
            @activate="hostService.filters.activateChip(chip)"
            @deactivate="hostService.filters.deactivateChip(chip)"
          />
        </div>
      </div>
      <RefreshCountdown
        :remaining="hostService.secondsRemaining.value"
        :interval="hostService.pollIntervalSeconds"
        :paused="hostService.paused.value"
        :manual-paused="hostService.manualPaused.value"
        size="small"
        @toggle="hostService.togglePause()"
      />
    </div>
    <MonitoringResultsCount
      class="monitoring-all-hosts-app__results-count"
      :active-filter-count="hostService.filters.activeFilterCount"
    />
    <MonitoringTable
      :rows="hostService.items.value"
      :loading="hostService.loading.value"
      :has-loaded="hostService.hasLoaded.value"
      :columns="columns"
      :filter-state="hostService.tableColumnFilters.value"
      :column-pinning="columnPinning"
      :get-row-key="rowKey"
      @update:filter-state="hostService.onColumnFiltersUpdate($event)"
    >
      <template #row="{ row, tableRow }">
        <HostRow :row="row" :table-row="tableRow" />
      </template>
      <template #empty-state>
        <MonitoringEmptyState />
      </template>
    </MonitoringTable>
  </div>
</template>

<style scoped>
.monitoring-all-hosts-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.monitoring-all-hosts-app__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
}

.monitoring-all-hosts-app__toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-all-hosts-app__search {
  flex: 1;
  max-width: 360px;
}

.monitoring-all-hosts-app__quick-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.monitoring-all-hosts-app__results-count {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 var(--spacing);
}
</style>
