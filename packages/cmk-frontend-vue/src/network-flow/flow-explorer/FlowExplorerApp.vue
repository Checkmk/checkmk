<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { NetworkFlowFlowExplorerApp } from 'cmk-shared-typing/typescript/network_flow/flow_explorer'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, onBeforeUnmount, onMounted, provide, useTemplateRef } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import MonitoringPagination from '@/monitoring/shared/components/MonitoringPagination.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'
import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'
import NetworkFlowSlideIns from '@/network-flow/slide-ins/NetworkFlowSlideIns.vue'
import { useNetworkFlowSlideIns } from '@/network-flow/slide-ins/useNetworkFlowSlideIns'

import { FlowApi, type FlowEntry } from './api/flows'
import { buildFlowColumnPinning, buildFlowColumns } from './columns'
import FlowRow from './components/FlowRow.vue'
import { csvFilename, downloadCsv, flowsToCsv } from './export/flowCsv'
import { TIME_FILTER_ID, defaultTimeFilter } from './filters/timeRange'
import { FlowService } from './services/FlowService'

const { _t } = usei18n()

const props = defineProps<NetworkFlowFlowExplorerApp>()

const columns = buildFlowColumns()
const columnPinning = buildFlowColumnPinning()

const defaultTimeRangeSeconds = computed(() => props.default_time_range_seconds ?? 0)

function defaultTimeContext(): ConfiguredFilters {
  return defaultTimeFilter(defaultTimeRangeSeconds.value)
}

// Python parses the "Network flow" filters out of the query string and hands
// them over as the page's context, so a filtered URL is all it takes to open a
// filtered listing - the controls for editing them come later. A URL naming no
// time range gets the page's default rather than the endpoint's shorter one.
function initialContext(): ConfiguredFilters {
  const fromUrl = structuredClone((props.filter_context ?? {}) as ConfiguredFilters)
  return fromUrl[TIME_FILTER_ID] === undefined ? { ...defaultTimeContext(), ...fromUrl } : fromUrl
}

const flowService = new FlowService(new FlowApi(), getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms ?? undefined,
  limitTiers: props.limit_tiers ?? undefined,
  columns,
  // Handed over at construction rather than on mount: the service fetches once
  // by itself, and setting the context afterwards would abort that request only
  // to repeat it - and aborting the request does not stop the query behind it.
  context: initialContext()
})

provide(MONITORING_SERVICE, flowService)

// Clicking an address or an autonomous system in a row opens its detail panel.
const slideIns = useNetworkFlowSlideIns()

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

onMounted(() => {
  flowService.onFocusSearch(() => searchInput.value?.focus())
})

onBeforeUnmount(() => {
  flowService.destruct()
})

// A flow record has no stable identity across pages on its own: ntopng reuses a
// FLOW_ID once a flow ends, so the start time disambiguates.
function rowKey(row: FlowEntry): string {
  return `${row.flow_id}-${row.first_seen}`
}

const canExport = computed(() => flowService.items.value.length > 0)

function exportCsv(): void {
  downloadCsv(csvFilename(Date.now()), flowsToCsv(flowService.items.value))
}
</script>

<template>
  <div class="network-flow-flow-explorer-app">
    <div class="network-flow-flow-explorer-app__header">
      <div class="network-flow-flow-explorer-app__toolbar">
        <CmkSearchInput
          ref="searchInput"
          v-model="flowService.searchQuery.value"
          class="network-flow-flow-explorer-app__search"
          :placeholder="_t('Search addresses, applications, protocols…')"
          @search="flowService.updateSearch($event)"
          @focusin="flowService.beginAutoPause()"
          @focusout="flowService.endAutoPause()"
        />
      </div>
      <div class="network-flow-flow-explorer-app__header-end">
        <RefreshCountdown
          :remaining="flowService.secondsRemaining.value"
          :interval="flowService.pollIntervalSeconds"
          :paused="flowService.paused.value"
          :manual-paused="flowService.manualPaused.value"
          size="small"
          @toggle="flowService.togglePause()"
        />
      </div>
    </div>
    <div class="network-flow-flow-explorer-app__table-toolbar">
      <div class="network-flow-flow-explorer-app__actions">
        <CmkButton
          variant="optional"
          :disabled="!canExport"
          :title="_t('Export the flows on this page as a CSV file')"
          @click="exportCsv"
        >
          <CmkIcon name="download-csv" size="small" />
          {{ _t('Export CSV') }}
        </CmkButton>
      </div>
      <div class="network-flow-flow-explorer-app__table-toolbar-end">
        <MonitoringPagination :unit="_t('flows')" />
        <MonitoringTotalCount />
        <MonitoringLimitSelector />
        <ColumnPicker />
      </div>
    </div>
    <MonitoringTable
      :rows="flowService.items.value"
      :fetch-state="flowService.fetchState.value"
      :has-loaded="flowService.hasLoaded.value"
      :columns="columns"
      :filter-state="flowService.tableColumnFilters.value"
      :column-pinning="columnPinning"
      :get-row-key="rowKey"
      @update:filter-state="flowService.onColumnFiltersUpdate($event)"
    >
      <template #row="{ row }">
        <FlowRow :row="row" />
      </template>
      <template #empty-state>
        <!-- The committed term rather than the live one: an empty listing was
             produced by the search that was sent, not by what is being typed. -->
        <MonitoringEmptyState :has-search-query="flowService.committedSearchQuery.value !== ''" />
      </template>
    </MonitoringTable>
    <NetworkFlowSlideIns :slide-ins="slideIns" />
  </div>
</template>

<style scoped>
.network-flow-flow-explorer-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.network-flow-flow-explorer-app__header {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.network-flow-flow-explorer-app__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--spacing);
}

.network-flow-flow-explorer-app__search {
  flex: 0 1 auto;
  max-width: 360px;
}

.network-flow-flow-explorer-app__header-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-left: auto;
}

/* Actions sit on the left and the counters on the right, the same split the
   All hosts table toolbar uses. */
.network-flow-flow-explorer-app__table-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.network-flow-flow-explorer-app__actions {
  display: flex;
  flex: 0 1 auto;
  align-items: center;
  gap: var(--spacing);
}

.network-flow-flow-explorer-app__table-toolbar-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-left: auto;
}

.network-flow-flow-explorer-app__table-toolbar-end > :not(:first-child) {
  border-left: 1px solid var(--font-color-dimmed);
  padding-left: var(--spacing);
}
</style>
