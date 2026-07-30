<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { NetworkFlowFlowExplorerApp } from 'cmk-shared-typing/typescript/network_flow/flow_explorer'
import usei18n from 'cmk-ui-library/lib/i18n'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { onBeforeUnmount, provide } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import MonitoringPagination from '@/monitoring/shared/components/MonitoringPagination.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'
import RefreshCountdown from '@/monitoring/shared/components/RefreshCountdown.vue'

import { FlowApi, type FlowEntry } from './api/flows'
import { buildFlowColumnPinning, buildFlowColumns } from './columns'
import FlowRow from './components/FlowRow.vue'
import { FlowService } from './services/FlowService'

const { _t } = usei18n()

const props = defineProps<NetworkFlowFlowExplorerApp>()

const columns = buildFlowColumns()
const columnPinning = buildFlowColumnPinning()

const flowService = new FlowService(new FlowApi(), getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms ?? undefined,
  limitTiers: props.limit_tiers ?? undefined,
  columns
})

provide(MONITORING_SERVICE, flowService)

onBeforeUnmount(() => {
  flowService.destruct()
})

// A flow record has no stable identity across pages on its own: ntopng reuses a
// FLOW_ID once a flow ends, so the start time disambiguates.
function rowKey(row: FlowEntry): string {
  return `${row.flow_id}-${row.first_seen}`
}
</script>

<template>
  <div class="network-flow-flow-explorer-app">
    <div class="network-flow-flow-explorer-app__header">
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
      <div class="network-flow-flow-explorer-app__actions" />
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
        <MonitoringEmptyState />
      </template>
    </MonitoringTable>
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing);
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
