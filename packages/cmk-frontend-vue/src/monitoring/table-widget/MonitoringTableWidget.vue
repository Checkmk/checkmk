<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import { computed, provide } from 'vue'

import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_TABLE_STATE } from '@/monitoring/shared/components/MonitoringTableContext'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'

import type { WidgetTableState } from './WidgetTableState'
import type { MonitoringTableDescriptor } from './tableDescriptors'

const props = defineProps<{
  descriptor: MonitoringTableDescriptor<T>
  columnIds: readonly string[]
  rows: T[]
  tableState: WidgetTableState
}>()

provide(MONITORING_TABLE_STATE, props.tableState)

const columns = computed(() => props.descriptor.columns(props.columnIds))
</script>

<template>
  <div class="monitoring-table-widget">
    <MonitoringTable
      :rows="rows"
      fetch-state="idle"
      :has-loaded="true"
      :columns="columns"
      :filter-state="[]"
      :get-row-key="(row: T) => descriptor.rowKey(row)"
    >
      <template #row="{ row, tableRow }">
        <component
          :is="descriptor.rowComponent"
          :row="row"
          :table-row="tableRow"
          :display-options="DEFAULT_DISPLAY_OPTIONS"
          :read-only="true"
        />
      </template>
      <template #empty-state>
        <MonitoringEmptyState />
      </template>
    </MonitoringTable>
  </div>
</template>

<style scoped>
.monitoring-table-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
</style>
