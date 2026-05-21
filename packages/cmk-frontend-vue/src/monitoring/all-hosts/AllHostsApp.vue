<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ColumnDef, type ColumnFiltersState, type SortingState } from '@tanstack/vue-table'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { onBeforeUnmount, ref } from 'vue'

import usei18n from '@/lib/i18n'

import type { HostEntry } from '@/monitoring/shared/api/types'

import MonitoringTable from '../shared/components/MonitoringTable.vue'
import { HostApi } from './api/hosts'
import HostRow from './components/HostRow.vue'
import { HostService } from './services/HostService'

const { _t } = usei18n()

const props = defineProps<MonitoringAllHostsApp>()

const hostService = new HostService(new HostApi(), props.poll_interval_ms)

onBeforeUnmount(() => {
  hostService.stopPolling()
})

const columns: ColumnDef<HostEntry>[] = [
  { accessorKey: 'state', header: _t('State') },
  { accessorKey: 'name', header: _t('Host') },
  { accessorKey: 'alias', header: _t('Alias') },
  { accessorKey: 'ip', header: _t('IP address') },
  { accessorKey: 'num_services_ok', header: _t('OK') },
  { accessorKey: 'num_services_warn', header: _t('Warn') },
  { accessorKey: 'num_services_crit', header: _t('Crit') },
  { accessorKey: 'num_services_unknown', header: _t('Unknown') },
  { accessorKey: 'num_services_pending', header: _t('Pending') }
]

const sortState = ref<SortingState>([])
const filterState = ref<ColumnFiltersState>([])

function rowKey(row: HostEntry): string {
  return `${row.site_id}/${row.name}`
}
</script>

<template>
  <MonitoringTable
    :rows="hostService.items.value"
    :loading="hostService.loading.value"
    :columns="columns"
    :sort-state="sortState"
    :filter-state="filterState"
    :get-row-key="rowKey"
    @update:sort-state="sortState = $event"
    @update:filter-state="filterState = $event"
  >
    <template #row="{ row }">
      <HostRow :row="row" />
    </template>
  </MonitoringTable>
</template>
