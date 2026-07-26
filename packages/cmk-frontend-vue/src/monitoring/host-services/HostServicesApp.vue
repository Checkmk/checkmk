<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ColumnDef } from '@tanstack/vue-table'
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { onMounted, ref } from 'vue'

import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import { HostServicesApi, type ServiceEntry } from './api/services'
import HostServicesRow from './components/HostServicesRow.vue'

const { _t } = usei18n()

const props = defineProps<MonitoringHostServicesApp>()

const api = new HostServicesApi()

const services = ref<ServiceEntry[]>([])
const fetchState = ref<FetchState>('foreground')
const hasLoaded = ref(false)

const columns: ColumnDef<ServiceEntry>[] = [
  {
    accessorKey: 'state',
    header: _t('State'),
    enableSorting: false,
    minSize: 74,
    maxSize: 100,
    meta: { justify: 'center' }
  },
  {
    accessorKey: 'name',
    header: _t('Service'),
    enableSorting: false,
    minSize: 150,
    maxSize: 350
  },
  {
    accessorKey: 'summary',
    header: _t('Summary'),
    enableSorting: false,
    minSize: 200
  },
  {
    accessorKey: 'last_check',
    header: _t('Last check'),
    enableSorting: false,
    minSize: 120,
    maxSize: 200
  },
  {
    accessorKey: 'last_state_change',
    header: _t('Last state change'),
    enableSorting: false,
    minSize: 120,
    maxSize: 200
  }
]

onMounted(async () => {
  try {
    services.value = await api.fetchServices(props.host, props.site)
  } finally {
    fetchState.value = 'idle'
    hasLoaded.value = true
  }
})

function navigateToLegacy(): void {
  if (props.legacy_view_button) {
    window.location.href = props.legacy_view_button.url
  }
}

function rowKey(row: ServiceEntry): string {
  return row.name
}
</script>

<template>
  <Teleport v-if="legacy_view_button" defer to=".titlebar">
    <CmkButton class="monitoring-host-services-app__legacy-view-button" @click="navigateToLegacy">
      <CmkIcon name="back" class="monitoring-host-services-app__legacy-view-button-icon" />
      {{ legacy_view_button.title }}
    </CmkButton>
  </Teleport>
  <div class="monitoring-host-services-app">
    <MonitoringTable
      :rows="services"
      :fetch-state="fetchState"
      :has-loaded="hasLoaded"
      :columns="columns"
      :filter-state="[]"
      :get-row-key="rowKey"
    >
      <template #row="{ row }">
        <HostServicesRow :row="row" />
      </template>
      <template #empty-state>
        <MonitoringEmptyState />
      </template>
    </MonitoringTable>
  </div>
</template>

<style scoped>
.monitoring-host-services-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.monitoring-host-services-app__legacy-view-button {
  right: var(--dimension-4);
  white-space: nowrap;
  align-self: center;
}

.monitoring-host-services-app__legacy-view-button-icon {
  margin-right: var(--dimension-3);
}
</style>
