<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ColumnDef, type ColumnFiltersState } from '@tanstack/vue-table'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { onBeforeUnmount, provide, ref } from 'vue'

import usei18n from '@/lib/i18n'

import type { HostEntry } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'

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

provide(MONITORING_SERVICE, hostService)

const columns: ColumnDef<HostEntry>[] = [
  { accessorKey: 'state', header: _t('State'), sortDescFirst: true, minSize: 60, maxSize: 130 },
  { accessorKey: 'name', header: _t('Host'), sortDescFirst: false, minSize: 150 },
  { accessorKey: 'alias', header: _t('Alias'), sortDescFirst: false, minSize: 150 },
  { accessorKey: 'ip', header: _t('IP address'), sortDescFirst: false, minSize: 100 },
  {
    accessorKey: 'num_services_ok',
    header: _t('OK'),
    sortDescFirst: true,
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_warn',
    header: _t('Warn'),
    sortDescFirst: true,
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_crit',
    header: _t('Crit'),
    sortDescFirst: true,
    meta: { justify: 'center' },
    minSize: 64,
    maxSize: 90
  },
  {
    accessorKey: 'num_services_unknown',
    header: _t('Unknown'),
    sortDescFirst: true,
    meta: { justify: 'center' },
    minSize: 92,
    maxSize: 130
  },
  {
    accessorKey: 'num_services_pending',
    header: _t('Pending'),
    sortDescFirst: true,
    meta: { justify: 'center' },
    minSize: 92,
    maxSize: 120
  }
]

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
    :filter-state="filterState"
    :get-row-key="rowKey"
    @update:filter-state="filterState = $event"
  >
    <template #row="{ row }">
      <HostRow :row="row" />
    </template>
  </MonitoringTable>
</template>
