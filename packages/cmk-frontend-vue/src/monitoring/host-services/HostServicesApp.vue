<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import { onMounted, ref } from 'vue'

import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import { HostServicesApi, type ServiceEntry } from './api/services'
import { useHostServicesColumns } from './columns'
import HostServicesRow from './components/HostServicesRow.vue'

const props = defineProps<MonitoringHostServicesApp>()

const api = new HostServicesApi()

const services = ref<ServiceEntry[]>([])
const fetchState = ref<FetchState>('foreground')
const hasLoaded = ref(false)

const columns = useHostServicesColumns()

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
