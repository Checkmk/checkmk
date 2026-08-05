<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, onBeforeUnmount, provide } from 'vue'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringResultsCount from '../shared/components/MonitoringResultsCount.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import MonitoringTotalCount from '../shared/components/MonitoringTotalCount.vue'
import RefreshCountdown from '../shared/components/RefreshCountdown.vue'
import { HostServicesApi } from './api/services'
import { useHostServicesColumns } from './columns'
import HostServicesRow from './components/HostServicesRow.vue'
import { HostServicesService } from './services/HostServicesService'

const props = defineProps<MonitoringHostServicesApp>()

const columns = useHostServicesColumns()

const hostServicesService = new HostServicesService(
  new HostServicesApi(),
  { name: props.host, site_id: props.site },
  getKeyShortcutServiceInstance(),
  {
    pollIntervalMs: props.poll_interval_ms,
    columns
  }
)

const isNarrowed = computed(() => hostServicesService.filters.activeFilterCount > 0)

onBeforeUnmount(() => {
  hostServicesService.destruct()
})

provide(MONITORING_SERVICE, hostServicesService)

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
      <MonitoringResultsCount :matched="hostServicesService.matched.value" :narrowed="isNarrowed" />
      <div class="monitoring-host-services-app__counts-end">
        <MonitoringTotalCount :total="hostServicesService.total.value" />
        <RefreshCountdown
          :remaining="hostServicesService.secondsRemaining.value"
          :interval="hostServicesService.pollIntervalSeconds"
          :paused="hostServicesService.paused.value"
          :manual-paused="hostServicesService.manualPaused.value"
          size="small"
          @toggle="hostServicesService.togglePause()"
        />
      </div>
    </div>
    <MonitoringTable
      :rows="hostServicesService.items.value"
      :fetch-state="hostServicesService.fetchState.value"
      :has-loaded="hostServicesService.hasLoaded.value"
      :columns="columns"
      :filter-state="hostServicesService.tableColumnFilters.value"
      :get-row-key="rowKey"
      @update:filter-state="hostServicesService.onColumnFiltersUpdate($event)"
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

.monitoring-host-services-app__counts-end {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}
</style>
