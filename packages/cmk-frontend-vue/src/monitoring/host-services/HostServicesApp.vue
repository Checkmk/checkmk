<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ColumnFiltersState } from '@tanstack/vue-table'
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import { computed, onMounted, ref } from 'vue'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringResultsCount from '../shared/components/MonitoringResultsCount.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import MonitoringTotalCount from '../shared/components/MonitoringTotalCount.vue'
import { HostServicesApi } from './api/services'
import { useHostServicesColumns } from './columns'
import HostServicesRow from './components/HostServicesRow.vue'

const props = defineProps<MonitoringHostServicesApp>()

const api = new HostServicesApi()

const services = ref<HostServiceEntry[]>([])
const matched = ref(0)
const total = ref(0)
const fetchState = ref<FetchState>('foreground')
const hasLoaded = ref(false)
const columnFilters = ref<ColumnFiltersState>([])

const columns = useHostServicesColumns()

const isNarrowed = computed(() => columnFilters.value.length > 0)

onMounted(async () => {
  try {
    const response = await api.fetchServices(props.host, props.site)
    services.value = response.services
    matched.value = response.meta.matched
    total.value = response.meta.total
  } finally {
    fetchState.value = 'idle'
    hasLoaded.value = true
  }
})

function rowKey(row: HostServiceEntry): string {
  return row.name
}
</script>

<template>
  <MonitoringSurveyLink url="https://survey.checkmk.com/index.php/852195?lang=en" />
  <MonitoringLegacyViewButton
    v-if="legacy_view_button"
    :title="legacy_view_button.title"
    :url="legacy_view_button.url"
  />
  <div class="monitoring-host-services-app">
    <div class="monitoring-host-services-app__counts">
      <MonitoringResultsCount :matched="matched" :narrowed="isNarrowed" />
      <MonitoringTotalCount :total="total" />
    </div>
    <MonitoringTable
      :rows="services"
      :fetch-state="fetchState"
      :has-loaded="hasLoaded"
      :columns="columns"
      :filter-state="columnFilters"
      :get-row-key="rowKey"
      @update:filter-state="columnFilters = $event"
    >
      <template #row="{ row }">
        <HostServicesRow :row="row" />
      </template>
      <template #empty-state>
        <MonitoringEmptyState :has-active-filter="isNarrowed" />
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

.monitoring-host-services-app__counts {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
}
</style>
