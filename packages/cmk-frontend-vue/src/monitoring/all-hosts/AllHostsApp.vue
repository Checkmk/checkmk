<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type ColumnDef,
  type ColumnPinningState,
  type RowSelectionState
} from '@tanstack/vue-table'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { computed, markRaw, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { getKeyShortcutServiceInstance } from '@/lib/keyShortcuts'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from '@/components/CmkIcon/types'
import CmkLink from '@/components/CmkLink.vue'
import CmkSearchInput from '@/components/CmkSearchInput.vue'
import CmkSlideInTabbed, { type SlideInTab } from '@/components/CmkSlideInTabbed'
import CmkSplitPane from '@/components/CmkSplitPane.vue'

import type { HostEntry, HostRef, HostState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import type {
  BooleanGroupFilter,
  CheckboxListFilter,
  NumericFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'
import { ACTION_REFRESH_DELAY_MS, HOST_LIMIT_TIERS } from '@/monitoring/shared/constants'

import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '../shared/components/MonitoringLimitSelector.vue'
import MonitoringResultsCount from '../shared/components/MonitoringResultsCount.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import MonitoringTruncationNotice from '../shared/components/MonitoringTruncationNotice.vue'
import RefreshCountdown from '../shared/components/RefreshCountdown.vue'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '../shared/components/action/ActionFeedback.vue'
import MonitoringActionBar from '../shared/components/action/MonitoringActionBar.vue'
import MonitoringActionPane from '../shared/components/action/MonitoringActionPane.vue'
import {
  ACK_ACTION_ID,
  useAcknowledgeAction
} from '../shared/components/action/actions/acknowledge'
import {
  RESCHEDULE_ACTION_ID,
  useRescheduleAction
} from '../shared/components/action/actions/reschedule'
import {
  SCHEDULE_DOWNTIME_ACTION_ID,
  useScheduleDowntimeAction
} from '../shared/components/action/actions/scheduleDowntime'
import { createActionRegistry } from '../shared/components/action/registry'
import { useMonitoringActions } from '../shared/services/useMonitoringActions'
import { HostActionMenuApi } from './api/actionMenu'
import { HostApi } from './api/hosts'
import HostRow from './components/HostRow.vue'
import HostOverviewSkeleton from './components/slide-in/HostOverviewSkeleton.vue'
import HostOverviewTab from './components/slide-in/HostOverviewTab.vue'
import HostSlideInActions from './components/slide-in/HostSlideInActions.vue'
import HostSlideInHeader from './components/slide-in/HostSlideInHeader.vue'
import { HostService } from './services/HostService'

const { _t } = usei18n()

const props = defineProps<MonitoringAllHostsApp>()

const ACTION_ICONS: Record<string, SimpleIcons> = {
  [ACK_ACTION_ID]: 'ack',
  [RESCHEDULE_ACTION_ID]: 'reload',
  [SCHEDULE_DOWNTIME_ACTION_ID]: 'downtime'
}

const hostActions: CellAction[] = (props.actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: ACTION_ICONS[action.ident] ?? 'action'
}))

// Always-visible inline buttons (edit host, parameters). Their url keeps the {host} placeholder,
// resolved per row in HostRow.
const rowActionButtons: CellAction[] = (props.row_actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: action.icon as SimpleIcons,
  url: action.url
}))

// Command entries the row dropdown runs immediately with their default values (no form), acting on
// that single host to mirror the legacy per-row action menu. Only list actions that are safe
// without user input — form-based ones (acknowledge, downtime) carry essential per-host input and
// must go through the action pane, not here. They carry no url, so ActionsCell emits `select`.
const IMMEDIATE_ROW_COMMAND_IDS: readonly string[] = [RESCHEDULE_ACTION_ID]

const rowCommands: CellAction[] = (props.actions ?? [])
  .filter((action) => IMMEDIATE_ROW_COMMAND_IDS.includes(action.ident))
  .map((action) => ({
    id: action.ident,
    label: action.title as TranslatedString,
    icon: ACTION_ICONS[action.ident] ?? 'action'
  }))

const hasRowActions = rowActionButtons.length > 0 || rowCommands.length > 0

const actionMenuApi = new HostActionMenuApi()

// Overflow-menu entries for a host: the immediate commands (reschedule) followed by the fetched
// legacy action-menu links (inventory, notes, topology, download, ...).
async function loadActionMenu(host: HostRef): Promise<CellAction[]> {
  const items = await actionMenuApi.fetchActionMenu(host)
  return [
    ...rowCommands,
    ...items.map((item) => ({
      id: `${item.title}|${item.url}`,
      label: item.title as TranslatedString,
      icon: item.icon_name as SimpleIcons,
      url: item.url,
      target: item.target
    }))
  ]
}

const stateFilter: CheckboxListFilter<'state'> = {
  type: 'checkbox-list',
  field: 'state',
  options: [
    { value: 'UP', title: _t('UP') },
    { value: 'DOWN', title: _t('DOWN') },
    { value: 'UNREACHABLE', title: _t('UNREACH') }
  ] satisfies { value: HostState; title: string }[]
}

const nameFilter: StringInputFilter<'name'> = {
  type: 'string-input',
  field: 'name'
}

const addressFilter: StringInputFilter<'address'> = {
  type: 'string-input',
  field: 'address'
}

const totalServicesFilter: NumericFilter<'num_services'> = {
  type: 'numeric',
  field: 'num_services'
}

const okServicesFilter: NumericFilter<'num_services_ok'> = {
  type: 'numeric',
  field: 'num_services_ok'
}

const warnServicesFilter: NumericFilter<'num_services_warn'> = {
  type: 'numeric',
  field: 'num_services_warn'
}

const critServicesFilter: NumericFilter<'num_services_crit'> = {
  type: 'numeric',
  field: 'num_services_crit'
}

const unknownServicesFilter: NumericFilter<'num_services_unknown'> = {
  type: 'numeric',
  field: 'num_services_unknown'
}

const pendingServicesFilter: NumericFilter<'num_services_pending'> = {
  type: 'numeric',
  field: 'num_services_pending'
}

const modesFilter: BooleanGroupFilter<'in_downtime' | 'acknowledged'> = {
  type: 'boolean-group',
  groups: [
    { field: 'in_downtime', title: _t('In downtime') },
    { field: 'acknowledged', title: _t('Acknowledged') }
  ]
}

const columns: ColumnDef<HostEntry>[] = [
  {
    id: 'select',
    header: '',
    enableSorting: false,
    minSize: 36,
    maxSize: 36,
    meta: { selectColumn: true, justify: 'center' }
  },
  {
    accessorKey: 'state',
    header: _t('State'),
    sortDescFirst: true,
    minSize: 74,
    maxSize: 100,
    meta: { filter: stateFilter }
  },
  {
    accessorKey: 'modes',
    header: _t('Mode'),
    enableSorting: false,
    minSize: 80,
    maxSize: 80,
    meta: { justify: 'left', filter: modesFilter }
  },
  {
    accessorKey: 'name',
    header: _t('Host'),
    sortDescFirst: false,
    minSize: 150,
    meta: { filter: nameFilter }
  },
  {
    accessorKey: 'address',
    header: _t('IP address'),
    sortDescFirst: false,
    minSize: 100,
    maxSize: 300,
    meta: { filter: addressFilter }
  },
  {
    accessorKey: 'num_services',
    header: _t('All services'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: totalServicesFilter,
      headerTitle: _t('Total number of services')
    },
    minSize: 70,
    maxSize: 130
  },
  {
    accessorKey: 'num_services_ok',
    header: _t('OK'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: okServicesFilter,
      headerTitle: _t('Number of services in OK state')
    },
    minSize: 70,
    maxSize: 70
  },
  {
    accessorKey: 'num_services_warn',
    header: _t('Wa'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: warnServicesFilter,
      headerTitle: _t('Number of services in warning state')
    },
    minSize: 70,
    maxSize: 70
  },
  {
    accessorKey: 'num_services_crit',
    header: _t('Cr'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: critServicesFilter,
      headerTitle: _t('Number of services in critical state')
    },
    minSize: 70,
    maxSize: 70
  },
  {
    accessorKey: 'num_services_unknown',
    header: _t('Un'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: unknownServicesFilter,
      headerTitle: _t('Number of services in unknown state')
    },
    minSize: 70,
    maxSize: 70
  },
  {
    accessorKey: 'num_services_pending',
    header: _t('Pd'),
    sortDescFirst: true,
    meta: {
      justify: 'right',
      filter: pendingServicesFilter,
      headerTitle: _t('Number of services in pending state')
    },
    minSize: 70,
    maxSize: 70
  },
  ...(hasRowActions
    ? [
        {
          id: 'actions',
          header: _t('Actions'),
          enableSorting: false,
          minSize: 75,
          maxSize: 75,
          meta: { justify: 'right' }
        } satisfies ColumnDef<HostEntry>
      ]
    : [])
]

const columnPinning: ColumnPinningState = {
  left: ['select', 'state', 'modes', 'name'],
  ...(hasRowActions ? { right: ['actions'] } : {})
}

const hostApi = new HostApi()

const hostService = new HostService(hostApi, getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms,
  limitTiers: HOST_LIMIT_TIERS,
  mayRemoveLimit: props.may_ignore_hard_limit ?? false,
  columns,
  quickFilters: [
    {
      label: _t('Unhandled host problems'),
      filter: {
        type: 'and',
        children: [
          {
            type: 'condition',
            field: 'state',
            op: 'one_of',
            value: ['DOWN', 'UNREACHABLE'] as HostState[]
          },
          { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
          { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
        ]
      }
    }
  ]
})

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

const rowSelection = ref<RowSelectionState>({})

const actionRegistry = createActionRegistry([
  useAcknowledgeAction(),
  useRescheduleAction(),
  useScheduleDowntimeAction()
])
const {
  activeAction,
  selectedCount,
  feedback,
  feedbackOpen,
  openAction,
  closeAction,
  applyFeedback
} = useMonitoringActions(rowSelection)

const selectedHosts = computed<HostRef[]>(() =>
  hostService.items.value
    .filter((host) => rowSelection.value[rowKey(host)])
    .map((host) => ({ site_id: host.site_id, name: host.name }))
)

onMounted(() => {
  hostService.onFocusSearch(() => searchInput.value?.focus())
})

onBeforeUnmount(() => {
  hostService.destruct()
})

provide(MONITORING_SERVICE, hostService)

function rowKey(row: HostEntry): string {
  return `${row.site_id}/${row.name}`
}

const slideInHost = ref<HostEntry | null>(null)
const slideInOpen = computed(() => slideInHost.value !== null)
const slideInActionId = ref<string | null>(null)

const slideInTargets = computed<HostRef[]>(() =>
  slideInHost.value ? [{ site_id: slideInHost.value.site_id, name: slideInHost.value.name }] : []
)

const slideInTabs = computed<SlideInTab[]>(() => {
  const host = slideInHost.value
  if (!host) {
    return []
  }
  return [
    {
      id: 'overview',
      title: _t('Overview'),
      component: markRaw(HostOverviewTab),
      skeleton: markRaw(HostOverviewSkeleton),
      load: () => hostApi.fetchHostOverview({ site_id: host.site_id, name: host.name }),
      props: { host }
    }
  ]
})

function openSlideIn(host: HostEntry): void {
  if (slideInHost.value === null) {
    hostService.beginAutoPause()
  }
  slideInActionId.value = null
  slideInHost.value = host
}

function closeSlideIn(): void {
  if (slideInHost.value !== null) {
    hostService.endAutoPause()
  }
  slideInHost.value = null
  slideInActionId.value = null
}

function openSlideInAction(actionId: string): void {
  if (actionId in actionRegistry) {
    slideInActionId.value = actionId
  }
}

function closeSlideInAction(): void {
  slideInActionId.value = null
}

function onSlideInActionFeedback(result: ActionFeedbackResult): void {
  feedback.value = result
  feedbackOpen.value = true
  slideInActionId.value = null
  if (result.variant === 'success') {
    hostService.refresh(ACTION_REFRESH_DELAY_MS)
  }
}

function onBulkActionFeedback(result: ActionFeedbackResult): void {
  applyFeedback(result)
  if (result.variant === 'success') {
    hostService.refresh(ACTION_REFRESH_DELAY_MS)
  }
}

function onBulkAction(action: CellAction): void {
  if (selectedHosts.value.length === 0 || !(action.id in actionRegistry)) {
    return
  }
  openAction(action.id)
}

async function onRowCommand(payload: { id: string; host: HostRef }): Promise<void> {
  const action = actionRegistry[payload.id]
  if (!action) {
    return
  }
  applyFeedback(await action.perform([payload.host], action.defaultValues()), {
    clearSelection: false
  })
}

function onRightPaneCollapse(collapsed: boolean): void {
  if (collapsed) {
    closeAction()
  }
}

function navigateToLegacy() {
  if (props.legacy_view_button) {
    window.location.href = props.legacy_view_button.url
  }
}
</script>

<template>
  <Teleport defer to=".titlebar">
    <CmkLink
      href="https://survey.checkmk.com/index.php/815511?lang=en"
      target="_blank"
      class="monitoring-all-hosts-app__survey-link"
    >
      <CmkIcon name="comment" class="monitoring-all-hosts-app__legacy-view-button-icon" />
      {{ _t('Give feedback on the new view') }}
    </CmkLink>
  </Teleport>
  <Teleport v-if="legacy_view_button" defer to=".titlebar">
    <CmkButton class="monitoring-all-hosts-app__legacy-view-button" @click="navigateToLegacy">
      <CmkIcon name="back" class="monitoring-all-hosts-app__legacy-view-button-icon" />
      {{ legacy_view_button.title }}
    </CmkButton>
  </Teleport>
  <div class="monitoring-all-hosts-app">
    <div class="monitoring-all-hosts-app__header">
      <div class="monitoring-all-hosts-app__toolbar">
        <CmkSearchInput
          ref="searchInput"
          v-model="hostService.searchQuery.value"
          class="monitoring-all-hosts-app__search"
          :placeholder="_t('Search hosts…')"
          @search="hostService.updateSearch($event)"
          @focusin="hostService.beginAutoPause()"
          @focusout="hostService.endAutoPause()"
        />
        <div class="monitoring-all-hosts-app__quick-filters">
          <QuickFilterChip
            v-for="chip in hostService.filters.quickFilters"
            :key="chip.label"
            :label="chip.label"
            :active="chip.isActive.value"
            @activate="hostService.activateQuickFilter(chip)"
            @deactivate="hostService.deactivateQuickFilter(chip)"
          />
        </div>
        <button
          class="monitoring-all-hosts-app__clear-filters"
          @click="hostService.clearAllFilters()"
        >
          {{ _t('Reset all filters') }}
        </button>
      </div>
      <div class="monitoring-all-hosts-app__header-end">
        <MonitoringLimitSelector />
        <RefreshCountdown
          :remaining="hostService.secondsRemaining.value"
          :interval="hostService.pollIntervalSeconds"
          :paused="hostService.paused.value"
          :manual-paused="hostService.manualPaused.value"
          size="small"
          @toggle="hostService.togglePause()"
        />
      </div>
    </div>
    <CmkSplitPane
      :collapsed="!activeAction"
      :right-min-size="30"
      :right-max-size="50"
      :collapsible-on-resize="false"
      class="monitoring-all-hosts-app__split"
      @update:collapsed="onRightPaneCollapse($event as boolean)"
    >
      <template #left>
        <div class="monitoring-all-hosts-app__left-pane">
          <MonitoringResultsCount class="monitoring-all-hosts-app__results-count" />
          <MonitoringTruncationNotice class="monitoring-all-hosts-app__truncation-notice" />
          <ActionFeedback
            v-if="feedback"
            v-model:open="feedbackOpen"
            class="monitoring-all-hosts-app__feedback"
            :feedback="feedback"
          />
          <MonitoringActionBar
            v-if="hostActions.length > 0"
            class="monitoring-all-hosts-app__action-bar"
            :selected-count="selectedCount"
            :actions="hostActions"
            @action="onBulkAction"
          />
          <MonitoringTable
            v-model:row-selection="rowSelection"
            :rows="hostService.items.value"
            :fetch-state="hostService.fetchState.value"
            :has-loaded="hostService.hasLoaded.value"
            :columns="columns"
            :filter-state="hostService.tableColumnFilters.value"
            :column-pinning="columnPinning"
            :get-row-key="rowKey"
            @update:filter-state="hostService.onColumnFiltersUpdate($event)"
          >
            <template #row="{ row, tableRow }">
              <HostRow
                :row="row"
                :table-row="tableRow"
                :row-actions="rowActionButtons"
                :load-action-menu="loadActionMenu"
                @open="openSlideIn"
                @command="onRowCommand"
              />
            </template>
            <template #empty-state>
              <MonitoringEmptyState />
            </template>
          </MonitoringTable>
        </div>
      </template>
      <template #right>
        <MonitoringActionPane
          v-if="activeAction"
          :action-id="activeAction"
          :actions="actionRegistry"
          :targets="selectedHosts"
          @feedback="onBulkActionFeedback"
          @cancel="closeAction"
        />
      </template>
    </CmkSplitPane>
    <CmkSlideInTabbed
      :open="slideInOpen"
      :tabs="slideInTabs"
      :override-active="slideInActionId !== null"
      :header="{ title: _t('Host details'), closeButton: true }"
      @close="closeSlideIn"
    >
      <template #above-tabs>
        <HostSlideInHeader v-if="slideInHost" :host="slideInHost" />
      </template>
      <template #actions>
        <HostSlideInActions @select="openSlideInAction" />
      </template>
      <template #override>
        <MonitoringActionPane
          v-if="slideInActionId"
          :action-id="slideInActionId"
          :actions="actionRegistry"
          :targets="slideInTargets"
          back-button
          indent
          :show-count="false"
          @back="closeSlideInAction"
          @cancel="closeSlideInAction"
          @feedback="onSlideInActionFeedback"
        />
      </template>
    </CmkSlideInTabbed>
  </div>
</template>

<style scoped>
.monitoring-all-hosts-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.monitoring-all-hosts-app__survey-link {
  margin-right: var(--dimension-6);
  place-content: center flex-end;
  align-items: center;
}

.monitoring-all-hosts-app__legacy-view-button {
  right: var(--dimension-4);
  white-space: nowrap;
  align-self: center;
}

.monitoring-all-hosts-app__legacy-view-button-icon {
  margin-right: var(--dimension-3);
}

.monitoring-all-hosts-app__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
}

.monitoring-all-hosts-app__toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-all-hosts-app__header-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-all-hosts-app__search {
  flex: 1;
  max-width: 360px;
}

.monitoring-all-hosts-app__quick-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.monitoring-all-hosts-app__clear-filters {
  border: 0;
  background-color: transparent;
  text-decoration: underline;
  font-weight: var(--font-weight-default);
  padding: 0;

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 2px;
  }

  &:hover {
    color: var(--color-corporate-green-50);
  }
}

.monitoring-all-hosts-app__split {
  flex: 1 1 auto;
  min-height: 0;
}

.monitoring-all-hosts-app__left-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.monitoring-all-hosts-app__results-count {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 var(--spacing);
}

.monitoring-all-hosts-app__truncation-notice {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 var(--spacing);
}

.monitoring-all-hosts-app__feedback {
  flex: 0 0 auto;
  margin: 0 0 var(--spacing);
}

.monitoring-all-hosts-app__action-bar {
  flex: 0 0 auto;
  margin-bottom: var(--spacing);
}
</style>
