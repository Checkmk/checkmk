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
import {
  type ConfiguredFilters,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import MonitoringPagination from '@/monitoring/shared/components/MonitoringPagination.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'
import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'
import NetworkFlowSlideIns from '@/network-flow/slide-ins/NetworkFlowSlideIns.vue'
import { useNetworkFlowSlideIns } from '@/network-flow/slide-ins/useNetworkFlowSlideIns'

import { FlowApi, type FlowEntry } from './api/flows'
import { buildFlowColumnPinning, buildFlowColumns } from './columns'
import FlowRow from './components/FlowRow.vue'
import { csvFilename, downloadCsv, flowsToCsv } from './export/flowCsv'
import { columnFiltersToContext, contextToColumnFilters } from './filters/columnFilters'
import {
  TIME_FILTER_ID,
  defaultTimeFilter,
  hasNonDefaultTime,
  withDefaultTime,
  withoutDefaultTime
} from './filters/timeRange'
import { flowFilterWriter } from './filters/urlFilters'
import { FlowService } from './services/FlowService'

const { _t } = usei18n()

const props = defineProps<NetworkFlowFlowExplorerApp>()

const columnPinning = buildFlowColumnPinning()

// Built once each, so the computed below only picks between two stable arrays.
// Rebuilding them inside the computed would hand the table a fresh column
// identity on every re-evaluation, which makes it rebuild its whole column model
// for no reason.
const columnsWithoutFilters = buildFlowColumns({ withFilters: false })
const columnsWithFilters = buildFlowColumns({ withFilters: true })

const defaultTimeRangeSeconds = computed(() => props.default_time_range_seconds ?? 0)

function defaultTimeContext(): ConfiguredFilters {
  return defaultTimeFilter(defaultTimeRangeSeconds.value)
}

/** The filters the page opened with; a URL naming no time range gets the default. */
function initialContext(): ConfiguredFilters {
  const fromUrl = structuredClone((props.filter_context ?? {}) as ConfiguredFilters)
  return fromUrl['network_flow_time'] === undefined
    ? { ...defaultTimeContext(), ...fromUrl }
    : fromUrl
}

const flowService = new FlowService(new FlowApi(), getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms ?? undefined,
  limitTiers: props.limit_tiers ?? undefined,
  columns: columnsWithoutFilters,
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

// A header funnel renders whatever its filter declares, so it needs the
// definitions the REST API serves; the funnels are withheld until they are in.
const { loadFilterDefinitions } = useProvideFilterDefinitions()
const filterDefinitionsLoaded = ref(false)

const columns = computed(() =>
  filterDefinitionsLoaded.value ? columnsWithFilters : columnsWithoutFilters
)

onMounted(async () => {
  await loadFilterDefinitions()
  filterDefinitionsLoaded.value = true
})

// The URL carries only what deviates from how the page opens, so clearing the
// filters leaves a bare URL instead of one spelling out the default window.
useUrlSync([
  flowFilterWriter(
    computed(() => withoutDefaultTime(flowService.context.value, defaultTimeRangeSeconds.value))
  )
])

function applyFilters(filters: ConfiguredFilters): void {
  flowService.setContext(filters)
}

const columnFilters = computed(() => contextToColumnFilters(flowService.context.value))

function onColumnFiltersUpdate(next: typeof columnFilters.value): void {
  // Clearing the Time funnel means "back to the default window", not "no window
  // at all" - dropping the bound would silently hand the range to the endpoint.
  applyFilters(
    withDefaultTime(
      columnFiltersToContext(flowService.context.value, next),
      defaultTimeRangeSeconds.value
    )
  )
}

// The time range is never "no filter" - it always has a window - so it only
// counts as filtered once it has been moved off the default. Anything else in
// the context, or a search term, counts on its own.
const hasActiveFilter = computed(
  () =>
    Object.keys(flowService.context.value).some((filterId) => filterId !== TIME_FILTER_ID) ||
    hasNonDefaultTime(flowService.context.value, defaultTimeRangeSeconds.value)
)

const hasFilters = computed(() => hasActiveFilter.value || flowService.searchQuery.value !== '')

/** Clears every filter and the search, back to the default time range. */
function clearAllFilters(): void {
  flowService.clearSearch()
  applyFilters(defaultTimeContext())
}

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
        <CmkButton
          variant="optional"
          :disabled="!canExport"
          :title="_t('Export the flows on this page as a CSV file')"
          @click="exportCsv"
        >
          <CmkIcon name="download-csv" size="small" />
          {{ _t('Export CSV') }}
        </CmkButton>
        <CmkButton v-if="hasFilters" variant="text" size="small" @click="clearAllFilters">
          {{ _t('Reset all filters') }}
        </CmkButton>
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
      :filter-state="columnFilters"
      :column-pinning="columnPinning"
      :get-row-key="rowKey"
      @update:filter-state="onColumnFiltersUpdate"
    >
      <template #row="{ row }">
        <FlowRow :row="row" />
      </template>
      <template #empty-state>
        <!-- The committed term rather than the live one: an empty listing was
             produced by the search that was sent, not by what is being typed. -->
        <MonitoringEmptyState
          :has-search-query="flowService.committedSearchQuery.value !== ''"
          :has-active-filter="hasActiveFilter"
        />
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
  align-items: center;
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

/* Only the counters remain here: the actions moved up next to the search box, so
   the table starts one row higher. */
.network-flow-flow-explorer-app__table-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
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
