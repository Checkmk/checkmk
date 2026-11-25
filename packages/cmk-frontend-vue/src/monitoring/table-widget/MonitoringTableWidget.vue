<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T extends RowWithModes, Target, Subject">
import type { ColumnPinningState } from '@tanstack/vue-table'
import { computed, provide, shallowRef } from 'vue'

import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import { MONITORING_TABLE_STATE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { RowCommand } from '@/monitoring/shared/components/action/rowCommand'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import {
  type RowWithModes,
  sizeIndicatorColumn,
  useIndicatorColumnWidth
} from '@/monitoring/shared/components/indicatorColumn'
import { sizeStateColumn, useStateIconCount } from '@/monitoring/shared/components/stateColumn'
import { ACTIONS_COLUMN_ID } from '@/monitoring/shared/constants'
import { sizeActionsColumn, useInlineCustomActionCount } from '@/monitoring/shared/customActions'
import type { DisplayOptions } from '@/monitoring/shared/types'

import type { WidgetTableState } from './WidgetTableState'
import type { MonitoringTableActions, MonitoringTableDescriptor } from './tableDescriptors'

const props = defineProps<{
  descriptor: MonitoringTableDescriptor<T, Target, Subject>
  columnIds: readonly string[]
  rows: T[]
  tableState: WidgetTableState
  displayOptions: DisplayOptions
  /**
   * What the reader may do with the rows, and the alerts of the page around that tell how the
   * commands picked in them go, one alert per command. Without it, the rows offer no actions.
   */
  actions?: MonitoringTableActions | undefined
  readOnly: boolean
}>()

const emit = defineEmits<{
  /** A command picked in a row ran, and the feedback tells how it went. */
  performed: [feedback: ActionOutcome]
}>()

provide(MONITORING_TABLE_STATE, props.tableState)

const rowActions = computed(() =>
  props.actions === undefined ? null : props.descriptor.rowActions(props.actions.offer)
)

const indicatorColumnWidth = useIndicatorColumnWidth(() => props.rows)
const stateIconCount = useStateIconCount(() => props.rows)
const inlineCustomActions = useInlineCustomActionCount(() => props.rows)

const columns = computed(() =>
  sizeStateColumn(
    sizeActionsColumn(
      sizeIndicatorColumn(
        props.descriptor.columns(
          rowActions.value === null ? props.columnIds : [...props.columnIds, ACTIONS_COLUMN_ID]
        ),
        indicatorColumnWidth.value
      ),
      inlineCustomActions.value
    ),
    stateIconCount.value
  )
)

const columnPinning = computed<ColumnPinningState>(() => ({
  right: rowActions.value === null ? [] : [ACTIONS_COLUMN_ID]
}))

const subject = shallowRef<Subject | null>(null)

function open(opened: Subject): void {
  subject.value = opened
}

function close(): void {
  subject.value = null
}

// The page around waits for the commands picked in the rows while the table reloads. A command
// picked again on the object it runs on, from the same row or another, is not run again.
async function onCommand(row: T, command: RowCommand<Target>): Promise<void> {
  const feedback = props.actions?.feedback
  const run = rowActions.value?.resolve(row, command)
  if (!run || !feedback) {
    return
  }
  const outcome = await feedback.track(run)
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
          :read-only="readOnly"
          v-on="descriptor.rowListeners(row, open)"
          @command="(command: RowCommand<Target>) => onCommand(row, command)"
        />
      </template>
      <template #empty-state>
        <MonitoringEmptyState />
      </template>
    </MonitoringTable>
    <component
      :is="descriptor.detailsComponent"
      :subject="subject"
      :offer="actions?.offer"
      :display-options="displayOptions"
      @close="close"
      @performed="(outcome: ActionOutcome) => emit('performed', outcome)"
    />
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
