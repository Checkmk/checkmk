<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T, Target">
import type { ColumnDef, ColumnPinningState, RowSelectionState } from '@tanstack/vue-table'
import CmkSplitPane from 'cmk-ui-library/components/CmkSplitPane.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import MonitoringResultsCount from '@/monitoring/shared/components/MonitoringResultsCount.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'
import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { useMonitoringActions } from '@/monitoring/shared/services/useMonitoringActions'

const props = withDefaults(
  defineProps<{
    service: MonitoringService<T>
    actions: MonitoringActionRegistry<Target>
    /** Entries offered by the action bar, acting on the current row selection. */
    bulkActions?: CellAction[]
    /** Names the rows the actions act on, e.g. "3 hosts selected". */
    selectionLabel: (count: number) => TranslatedString
    /** Names the action bar for screen readers, e.g. "Actions for selected hosts". */
    actionsLabel: TranslatedString
    /** Relates the selection to the loaded rows in the action pane's subtitle. */
    countsLabel: (selected: number, total: number) => TranslatedString
    columns: ColumnDef<T>[]
    columnPinning: ColumnPinningState
    getRowKey: (row: T) => string
    /** Maps a row to the reference the actions act on. */
    getActionTarget: (row: T) => Target
    /**
     * Actions that skip the form and run straight away on a single selected row,
     * because their default values need no input.
     */
    immediateActionIds?: readonly string[]
  }>(),
  { bulkActions: () => [], immediateActionIds: () => [] }
)

const emit = defineEmits<{
  (event: 'performed', result: ActionFeedbackResult): void
}>()

const rowSelection = ref<RowSelectionState>({})
const runningActionId = ref<string | null>(null)

const selectableKeys = computed<string[]>(() =>
  props.service.items.value.map((row) => props.getRowKey(row))
)

const {
  activeAction,
  selectedCount,
  feedback,
  feedbackOpen,
  openAction,
  closeAction,
  applyFeedback
} = useMonitoringActions(rowSelection, selectableKeys)

const selectedTargets = computed<Target[]>(() =>
  props.service.items.value
    .filter((row) => rowSelection.value[props.getRowKey(row)])
    .map((row) => props.getActionTarget(row))
)

const isNarrowed = computed(
  () =>
    props.service.filters.activeFilterCount > 0 || props.service.committedSearchQuery.value !== ''
)

function onFeedback(result: ActionFeedbackResult): void {
  applyFeedback(result)
  emit('performed', result)
}

async function onBulkAction(action: CellAction): Promise<void> {
  const registered = props.actions[action.id]
  if (!registered || selectedTargets.value.length === 0) {
    return
  }
  if (props.immediateActionIds.includes(action.id) && selectedTargets.value.length === 1) {
    runningActionId.value = action.id
    try {
      onFeedback(await registered.perform(selectedTargets.value, registered.defaultValues()))
    } finally {
      runningActionId.value = null
    }
    return
  }
  openAction(action.id)
}

async function onRowCommand(payload: { id: string; target: Target }): Promise<void> {
  const action = props.actions[payload.id]
  if (!action) {
    return
  }
  applyFeedback(await action.perform([payload.target], action.defaultValues()), {
    clearSelection: false
  })
}

function onRightPaneCollapse(collapsed: boolean): void {
  if (collapsed) {
    closeAction()
  }
}
</script>

<template>
  <CmkSplitPane
    :collapsed="!activeAction"
    :right-min-size="30"
    :right-max-size="50"
    :collapsible-on-resize="false"
    class="monitoring-split-pane"
    @update:collapsed="onRightPaneCollapse($event as boolean)"
  >
    <template #left>
      <div class="monitoring-split-pane__left-pane">
        <MonitoringResultsCount
          class="monitoring-split-pane__results-count"
          :matched="service.matched.value"
          :narrowed="isNarrowed"
        />
        <ActionFeedback
          v-if="feedback"
          v-model:open="feedbackOpen"
          class="monitoring-split-pane__feedback"
          :feedback="feedback"
        />
        <div class="monitoring-split-pane__table-toolbar">
          <MonitoringActionBar
            v-if="bulkActions.length > 0"
            class="monitoring-split-pane__action-bar"
            :selected-count="selectedCount"
            :actions="bulkActions"
            :selection-label="selectionLabel(selectedCount)"
            :label="actionsLabel"
            :running-action-id="runningActionId"
            @action="onBulkAction"
          />
          <div class="monitoring-split-pane__table-toolbar-end">
            <MonitoringTotalCount :total="service.total.value" />
            <MonitoringLimitSelector />
            <ColumnPicker />
          </div>
        </div>
        <MonitoringTable
          v-model:row-selection="rowSelection"
          :rows="service.items.value"
          :fetch-state="service.fetchState.value"
          :has-loaded="service.hasLoaded.value"
          :columns="columns"
          :filter-state="service.tableColumnFilters.value"
          :column-pinning="columnPinning"
          :get-row-key="getRowKey"
          @update:filter-state="service.onColumnFiltersUpdate($event)"
        >
          <template #row="{ row, tableRow }">
            <slot name="row" :row="row" :table-row="tableRow" :on-command="onRowCommand" />
          </template>
          <template #empty-state>
            <slot name="empty-state">
              <MonitoringEmptyState
                :has-search-query="service.committedSearchQuery.value !== ''"
                :has-active-filter="service.filters.activeFilterCount > 0"
              />
            </slot>
          </template>
        </MonitoringTable>
      </div>
    </template>
    <template #right>
      <MonitoringActionPane
        v-if="activeAction"
        :action-id="activeAction"
        :actions="actions"
        :targets="selectedTargets"
        :show-close="true"
        :counts-label="countsLabel"
        @feedback="onFeedback"
        @cancel="closeAction"
      />
    </template>
  </CmkSplitPane>
</template>

<style scoped>
.monitoring-split-pane {
  flex: 1 1 auto;
  min-height: 0;
}

.monitoring-split-pane__left-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.monitoring-split-pane__results-count {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 var(--spacing);
}

.monitoring-split-pane__feedback {
  flex: 0 0 auto;
  margin: 0 0 var(--spacing);
}

.monitoring-split-pane__table-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.monitoring-split-pane__action-bar {
  flex: 0 1 auto;
}

.monitoring-split-pane__table-toolbar-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-left: auto;
}

.monitoring-split-pane__table-toolbar-end > :not(:first-child) {
  border-left: 1px solid var(--font-color-dimmed);
  padding-left: var(--spacing);
}
</style>
