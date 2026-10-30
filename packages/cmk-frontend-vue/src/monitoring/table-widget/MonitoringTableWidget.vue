<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T, Target">
import type { ColumnPinningState } from '@tanstack/vue-table'
import { computed, provide } from 'vue'

import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_TABLE_STATE } from '@/monitoring/shared/components/MonitoringTableContext'
import {
  type RowCommand,
  useRowCommandRunner
} from '@/monitoring/shared/components/action/rowCommand'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { ACTIONS_COLUMN_ID } from '@/monitoring/shared/constants'
import type { DisplayOptions } from '@/monitoring/shared/types'

import type { WidgetTableState } from './WidgetTableState'
import type { MonitoringTableActionOffer, MonitoringTableDescriptor } from './tableDescriptors'

const props = defineProps<{
  descriptor: MonitoringTableDescriptor<T, Target>
  columnIds: readonly string[]
  rows: T[]
  tableState: WidgetTableState
  displayOptions: DisplayOptions
  /** What the reader may do with the rows. Without it, the rows offer no actions. */
  actionOffer?: MonitoringTableActionOffer | undefined
}>()

const emit = defineEmits<{
  /** A command picked in a row ran, and the feedback tells how it went. */
  performed: [feedback: ActionOutcome]
}>()

provide(MONITORING_TABLE_STATE, props.tableState)

const rowActions = computed(() =>
  props.actionOffer === undefined ? null : props.descriptor.rowActions(props.actionOffer)
)

const columns = computed(() =>
  props.descriptor.columns(
    rowActions.value === null ? props.columnIds : [...props.columnIds, ACTIONS_COLUMN_ID]
  )
)

const columnPinning = computed<ColumnPinningState>(() => ({
  right: rowActions.value === null ? [] : [ACTIONS_COLUMN_ID]
}))

const rowCommands = useRowCommandRunner()

async function onCommand(row: T, command: RowCommand<Target>): Promise<void> {
  const actions = rowActions.value
  if (actions === null) {
    return
  }
  const outcome = await rowCommands.run(props.descriptor.rowKey(row), (signal) =>
    actions.run(row, command, signal)
  )
  if (outcome) {
    emit('performed', outcome)
  }
}
</script>

<template>
  <div class="monitoring-table-widget">
    <MonitoringTable
      :rows="rows"
      fetch-state="idle"
      :has-loaded="true"
      :columns="columns"
      :column-pinning="columnPinning"
      :filter-state="[]"
      :get-row-key="(row: T) => descriptor.rowKey(row)"
    >
      <template #row="{ row, tableRow }">
        <component
          :is="descriptor.rowComponent"
          v-bind="rowActions?.rowProps(row)"
          :row="row"
          :table-row="tableRow"
          :display-options="displayOptions"
          :read-only="true"
          :busy="rowCommands.isBusy(descriptor.rowKey(row))"
          @command="(command: RowCommand<Target>) => onCommand(row, command)"
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
