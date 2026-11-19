<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T, Target">
import type { ColumnDef, ColumnPinningState, RowSelectionState } from '@tanstack/vue-table'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkSplitPane from 'cmk-ui-library/components/CmkSplitPane.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

import ColumnPicker from '@/monitoring/shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '@/monitoring/shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '@/monitoring/shared/components/MonitoringLimitSelector.vue'
import MonitoringResultsCount from '@/monitoring/shared/components/MonitoringResultsCount.vue'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'
import ActionFeedbackAlerts from '@/monitoring/shared/components/action/ActionFeedbackAlerts.vue'
import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import {
  type RowCommand,
  resolveRowCommand
} from '@/monitoring/shared/components/action/rowCommand'
import { type ActionRun, prepareRun } from '@/monitoring/shared/components/action/run'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { ACTION_PANE_MIN_WIDTH } from '@/monitoring/shared/constants'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { useMonitoringActions } from '@/monitoring/shared/services/useMonitoringActions'
import { unreachableSitesHeading, unreachableSitesHint } from '@/monitoring/shared/unreachableSites'

const props = withDefaults(
  defineProps<{
    service: MonitoringService<T>
    actions: MonitoringActionRegistry<Target>
    /** Entries offered by the action bar, acting on the current row selection. */
    bulkActions?: CellAction[]
    /** Entries of the action bar's "More" menu, acting on the selection as well. */
    moreActions?: CellAction[]
    /** Names the rows the actions act on, e.g. "Selected hosts: 3". */
    selectionLabel: (count: number) => TranslatedString
    /** Names the action bar for screen readers, e.g. "Actions for selected hosts". */
    actionsLabel: TranslatedString
    /** Relates the selection to the loaded rows in the action pane's subtitle. */
    countsLabel: (selected: number, total: number) => TranslatedString
    columns: ColumnDef<T>[]
    columnPinning: ColumnPinningState
    getRowKey: (row: T) => string
    /** Opens the details of a row clicked anywhere outside its own click targets. */
    openRow?: ((row: T) => void) | undefined
    /** Maps a row to the reference the actions act on. */
    getActionTarget: (row: T) => Target
    /** The same key for every reference to the same object, e.g. from different rows. */
    getTargetKey: (target: Target) => string
    /**
     * Maps the selected rows to what a given action acts on, for pages where that is not simply
     * one target per row. Defaults to `getActionTarget` on each row.
     */
    getActionTargets?: ((rows: T[], actionId: string) => Target[]) | undefined
    /**
     * Actions that skip the form and run straight away on a single selected row,
     * because their default values need no input.
     */
    immediateActionIds?: readonly string[]
  }>(),
  { bulkActions: () => [], moreActions: () => [], immediateActionIds: () => [] }
)

const emit = defineEmits<{
  (event: 'performed', result: ActionOutcome): void
}>()

const { _t } = usei18n()

const rowSelection = ref<RowSelectionState>({})
const runningActionId = ref<string | null>(null)
/** The action awaiting confirmation in the alert above the table. */
const confirmingActionId = ref<string | null>(null)
const displayOptionsOpen = ref(false)

const selectableKeys = computed<string[]>(() =>
  props.service.items.value.map((row) => props.getRowKey(row))
)

const { activeAction, selectedCount, feedback, openAction, closeAction, applyFeedback } =
  useMonitoringActions(rowSelection, selectableKeys)

function targetsFor(actionId: string): Target[] {
  const rows = props.service.items.value.filter((row) => rowSelection.value[props.getRowKey(row)])
  return props.getActionTargets
    ? props.getActionTargets(rows, actionId)
    : rows.map((row) => props.getActionTarget(row))
}

const noTargetsFeedback: ActionOutcome = {
  variant: 'error',
  message: _t('This action cannot be performed on any of the selected rows.')
}

const confirmation = computed(() => {
  const id = confirmingActionId.value
  const action = id === null ? undefined : props.actions[id]
  const targets = id === null ? [] : targetsFor(id)
  const count = targets.length
  return (
    action?.confirm && {
      title: action.title,
      // Both lines are translated on their own; the alert keeps the line break.
      text: `${props.countsLabel(selectedCount.value, props.service.total.value)}\n${action.confirm.detail(count, targets)}` as TranslatedString,
      submitLabel: action.confirm.submitLabel(count)
    }
  )
})

watch(selectedCount, (count) => {
  if (count === 0) {
    confirmingActionId.value = null
  }
})

async function onConfirm(): Promise<void> {
  const id = confirmingActionId.value
  const action = id === null ? undefined : props.actions[id]
  confirmingActionId.value = null
  if (id === null || !action) {
    return
  }
  // The selection may have changed while the confirmation was shown.
  const targets = targetsFor(id)
  if (targets.length === 0) {
    applyFeedback(noTargetsFeedback)
    return
  }
  runningActionId.value = id
  try {
    await runOutsidePane(prepareRun(action, targets))
  } finally {
    runningActionId.value = null
  }
}

const isNarrowed = computed(
  () =>
    props.service.filters.activeFilterCount > 0 || props.service.committedSearchQuery.value !== ''
)

const hasUnreachableSites = computed(() => props.service.unreachableSites.value.length > 0)
const unreachableSitesTitle = computed(() =>
  unreachableSitesHeading(props.service.unreachableSites.value)
)
const unreachableSitesText = computed(() =>
  unreachableSitesHint(props.service.unreachableSites.value)
)

function onFeedback(result: ActionOutcome): void {
  applyFeedback(result)
  emit('performed', result)
}

// A command run outside the pane - from a row, at once or once confirmed - may take a while, as a
// reschedule waits for its check: an alert tells it runs, and its outcome leaves alone a pane the
// user has opened meanwhile. It runs on for as long as its alert is on show.
async function runOutsidePane(run: ActionRun): Promise<void> {
  const outcome = await feedback.track(run)
  if (outcome) {
    emit('performed', outcome)
  }
}

async function onBulkAction(action: CellAction): Promise<void> {
  const registered = props.actions[action.id]
  if (!registered || selectedCount.value === 0) {
    return
  }
  const targets = targetsFor(action.id)
  if (targets.length === 0) {
    applyFeedback(noTargetsFeedback)
    return
  }
  if (props.immediateActionIds.includes(action.id) && selectedCount.value === 1) {
    closeAction()
    runningActionId.value = action.id
    try {
      await runOutsidePane(prepareRun(registered, targets))
    } finally {
      runningActionId.value = null
    }
    return
  }
  displayOptionsOpen.value = false
  if (registered.confirm) {
    closeAction()
    confirmingActionId.value = action.id
    return
  }
  confirmingActionId.value = null
  openAction(action.id)
}

function toggleDisplayOptions(): void {
  if (displayOptionsOpen.value) {
    displayOptionsOpen.value = false
    return
  }
  closeAction()
  displayOptionsOpen.value = true
}

// A command picked again on the object it runs on, from the same row or another, is not run again.
// One picked in the action bar runs on the selection as asked, whatever runs in the rows meanwhile.
async function onRowCommand(command: RowCommand<Target>): Promise<void> {
  const run = resolveRowCommand(props.actions, command, props.getTargetKey)
  if (run) {
    await runOutsidePane(run)
  }
}

function onRightPaneCollapse(collapsed: boolean): void {
  if (collapsed) {
    closeAction()
    displayOptionsOpen.value = false
  }
}
</script>

<template>
  <CmkSplitPane
    :collapsed="!activeAction && !displayOptionsOpen"
    :pane-min-size="30"
    :pane-max-size="50"
    :pane-min-width="ACTION_PANE_MIN_WIDTH"
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
        <ActionFeedbackAlerts class="monitoring-split-pane__feedback" :stack="feedback" />
        <CmkAlert
          v-if="hasUnreachableSites"
          class="monitoring-split-pane__unreachable-sites"
          variant="warning"
          :heading="unreachableSitesTitle"
          :text="unreachableSitesText"
        />
        <CmkAlert
          v-if="confirmation"
          class="monitoring-split-pane__confirmation"
          variant="warning"
          :heading="confirmation.title"
          :text="confirmation.text"
          :main-button="{ title: confirmation.submitLabel, onclick: onConfirm }"
          :optional-button="{
            title: _t('Cancel'),
            icon: 'cancel',
            onclick: () => (confirmingActionId = null)
          }"
        />
        <div class="monitoring-split-pane__table-toolbar">
          <MonitoringActionBar
            v-if="bulkActions.length + moreActions.length > 0"
            class="monitoring-split-pane__action-bar"
            :selected-count="selectedCount"
            :actions="bulkActions"
            :more-actions="moreActions"
            :selection-label="selectionLabel(selectedCount)"
            :label="actionsLabel"
            :running-action-id="runningActionId"
            @action="onBulkAction"
          />
          <div class="monitoring-split-pane__table-toolbar-end">
            <div class="monitoring-split-pane__table-toolbar-stats">
              <MonitoringTotalCount :total="service.total.value" :partial="hasUnreachableSites" />
              <MonitoringLimitSelector />
            </div>
            <div class="monitoring-split-pane__table-toolbar-controls">
              <ColumnPicker />
              <CmkButton
                variant="optional"
                size="iconOnly"
                :title="_t('Modify display options')"
                :aria-label="_t('Modify display options')"
                @click="toggleDisplayOptions"
              >
                <CmkMultitoneIcon
                  name="display-options"
                  primary-color="font"
                  :secondary-color="{ custom: 'var(--font-color-dimmed)' }"
                  size="small"
                />
              </CmkButton>
            </div>
          </div>
        </div>
        <MonitoringTable
          v-model:row-selection="rowSelection"
          :rows="service.items.value"
          :fetch-state="service.fetchState.value"
          :has-loaded="service.hasLoaded.value"
          :load-failed="service.loadFailed.value"
          :columns="columns"
          :filter-state="service.tableColumnFilters.value"
          :column-pinning="columnPinning"
          :get-row-key="getRowKey"
          :open-row="openRow"
          @update:filter-state="service.onColumnFiltersUpdate($event)"
          @retry="service.retry()"
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
      <!-- Another action is a new pane: the one before stops waiting for what it ran. -->
      <MonitoringActionPane
        v-if="activeAction"
        :key="activeAction"
        :action-id="activeAction"
        :actions="actions"
        :targets="targetsFor(activeAction)"
        :show-close="true"
        :counts-label="countsLabel"
        @feedback="onFeedback"
        @cancel="closeAction"
      />
      <slot
        v-else-if="displayOptionsOpen"
        name="display-options"
        :close="() => (displayOptionsOpen = false)"
      />
    </template>
  </CmkSplitPane>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;
@use './monitoringLayout' as layout;

.monitoring-split-pane {
  flex: 1 1 auto;
  min-height: 0;
}

.monitoring-split-pane__left-pane {
  /* Below this content width the toolbar can no longer keep the action bar and the total/limit
     controls apart, so the pane stops shrinking and the panel scrolls horizontally instead. */
  box-sizing: border-box;
  min-width: layout.$min-content-width;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0 var(--spacing) 0 0;

  /* The panel is resized by dragging the split handle or opening the right pane, so the
     responsive layout of the toolbar below must follow this element, not the viewport. */
  container-type: inline-size;
}

.monitoring-split-pane__results-count {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 var(--spacing);
}

.monitoring-split-pane__feedback,
.monitoring-split-pane__unreachable-sites {
  flex: 0 0 auto;
  margin: 0 0 var(--spacing);
}

.monitoring-split-pane__confirmation {
  flex: 0 0 auto;
  margin: 0 0 var(--spacing);

  :deep(.cmk-alert__body) {
    white-space: pre-line;
  }
}

.monitoring-split-pane__table-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

/* The action bar and the end group always share one line: the bar gives way (its buttons wrap
   and collapse to icons), the end group keeps its size. */
.monitoring-split-pane__action-bar {
  flex: 0 1 auto;
  min-width: 0;
}

.monitoring-split-pane__table-toolbar-end {
  --table-toolbar-separator-gap: var(--dimension-4);

  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: calc(var(--table-toolbar-separator-gap) * 2);
  margin-left: auto;
}

.monitoring-split-pane__table-toolbar-stats,
.monitoring-split-pane__table-toolbar-controls {
  display: flex;
  align-items: center;
}

.monitoring-split-pane__table-toolbar-stats {
  gap: calc(var(--table-toolbar-separator-gap) * 2);
}

.monitoring-split-pane__table-toolbar-controls {
  gap: var(--dimension-3);
}

/* Separators between the total count, the row limit and the controls. */
.monitoring-split-pane__table-toolbar-stats > :not(:first-child),
.monitoring-split-pane__table-toolbar-controls > :first-child {
  position: relative;
}

.monitoring-split-pane__table-toolbar-stats > :not(:first-child)::before,
.monitoring-split-pane__table-toolbar-controls > :first-child::before {
  content: '';
  position: absolute;
  top: 50%;
  left: calc(var(--table-toolbar-separator-gap) * -1);
  height: var(--dimension-7);
  transform: translateY(-50%);
  border-left: 1px solid var(--font-color-dimmed);
}

/* M and smaller: the column picker and the display options button break onto their own row below
   the total count and the row limit, and the group only takes the width of its widest row. */
@include bp.container-below(l) {
  .monitoring-split-pane__table-toolbar-end {
    flex-direction: column;
    align-items: flex-end;
    gap: var(--spacing);
  }

  /* The picker now starts a row, so it needs no separator. */
  .monitoring-split-pane__table-toolbar-controls > :first-child::before {
    display: none;
  }
}
</style>
