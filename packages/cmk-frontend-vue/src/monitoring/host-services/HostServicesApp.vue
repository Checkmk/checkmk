<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { RowSelectionState } from '@tanstack/vue-table'
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import type { HostRef, HostServiceEntry } from '@/monitoring/shared/api/types'
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
import ServiceSlideIn from './components/ServiceSlideIn.vue'
import { HostServicesService } from './services/HostServicesService'

const { _t } = usei18n()

const props = defineProps<MonitoringHostServicesApp>()

const rowSelection = ref<RowSelectionState>({})

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

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

const isNarrowed = computed(
  () =>
    hostServicesService.filters.activeFilterCount > 0 ||
    hostServicesService.committedSearchQuery.value !== ''
)

onMounted(() => {
  hostServicesService.onFocusSearch(() => searchInput.value?.focus())
})

onBeforeUnmount(() => {
  hostServicesService.destruct()
})

provide(MONITORING_SERVICE, hostServicesService)

function rowKey(row: HostServiceEntry): string {
  return row.name
}

const hostRef: HostRef = { name: props.host, site_id: props.site }

const slideInService = ref<HostServiceEntry | null>(null)

function openSlideIn(service: HostServiceEntry): void {
  if (slideInService.value === null) {
    hostServicesService.beginAutoPause()
  }
  slideInService.value = service
}

function closeSlideIn(): void {
  if (slideInService.value !== null) {
    hostServicesService.endAutoPause()
  }
  slideInService.value = null
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
    <div class="monitoring-host-services-app__header">
      <CmkSearchInput
        ref="searchInput"
        v-model="hostServicesService.searchQuery.value"
        class="monitoring-host-services-app__search"
        :placeholder="_t('Search services…')"
        @search="hostServicesService.updateSearch($event)"
        @focusin="hostServicesService.beginAutoPause()"
        @focusout="hostServicesService.endAutoPause()"
      />
    </div>
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
      v-model:row-selection="rowSelection"
      :rows="hostServicesService.items.value"
      :fetch-state="hostServicesService.fetchState.value"
      :has-loaded="hostServicesService.hasLoaded.value"
      :columns="columns"
      :filter-state="hostServicesService.tableColumnFilters.value"
      :get-row-key="rowKey"
      @update:filter-state="hostServicesService.onColumnFiltersUpdate($event)"
    >
      <template #row="{ row, tableRow }">
        <HostServicesRow :row="row" :table-row="tableRow" @open="openSlideIn" />
      </template>
      <template #empty-state>
        <MonitoringEmptyState
          :has-search-query="hostServicesService.committedSearchQuery.value !== ''"
          :has-active-filter="hostServicesService.filters.activeFilterCount > 0"
        />
      </template>
    </MonitoringTable>
    <ServiceSlideIn :service="slideInService" :host="hostRef" @close="closeSlideIn" />
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

.monitoring-host-services-app__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-services-app__search {
  flex: 1;
  max-width: 360px;
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
