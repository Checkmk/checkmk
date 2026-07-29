<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type RowSelectionState } from '@tanstack/vue-table'
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import CmkSplitPane from 'cmk-ui-library/components/CmkSplitPane.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, markRaw, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import type { HostEntry, HostRef, HostState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import { ACTION_REFRESH_DELAY_MS, HOST_LIMIT_TIERS } from '@/monitoring/shared/constants'

import ColumnPicker from '../shared/components/ColumnPicker.vue'
import MonitoringEmptyState from '../shared/components/MonitoringEmptyState.vue'
import MonitoringLimitSelector from '../shared/components/MonitoringLimitSelector.vue'
import MonitoringResultsCount from '../shared/components/MonitoringResultsCount.vue'
import MonitoringTable from '../shared/components/MonitoringTable.vue'
import MonitoringTotalCount from '../shared/components/MonitoringTotalCount.vue'
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
import { buildHostColumnPinning, buildHostColumns } from './columns'
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

const columns = buildHostColumns({ includeActions: hasRowActions })
const columnPinning = buildHostColumnPinning({ includeActions: hasRowActions })

const hostApi = new HostApi()

const hostService = new HostService(hostApi, getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms,
  limitTiers: HOST_LIMIT_TIERS,
  mayRemoveLimit: props.may_ignore_hard_limit ?? false,
  columns,
  quickFilters: [
    {
      label: _t('Unhandled host problems'),
      tooltip: _t(
        'Show only hosts in a problem state (DOWN or UNREACH) that are neither acknowledged nor in a scheduled downtime'
      ),
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

const slideInInlineActions = computed<CellAction[]>(() => {
  const host = slideInHost.value
  if (!host) {
    return []
  }
  const name = host.name
  const statusAction: CellAction = {
    id: 'show_status',
    label: _t('Show status of host %{name}', { name }),
    icon: 'folder',
    url: host.legacy_host_status_link
  }
  const resolved = rowActionButtons.map((action) => ({
    ...action,
    label: action.id === 'edit' ? _t('Edit host %{name}', { name }) : action.label,
    url: action.url?.replace('{host}', encodeURIComponent(name))
  }))
  return [statusAction, ...resolved]
})

const slideInLoadActionMenu = computed<(() => Promise<CellAction[]>) | undefined>(() => {
  const host = slideInHost.value
  if (!host) {
    return undefined
  }
  const hostRef: HostRef = { site_id: host.site_id, name: host.name }
  return () => loadActionMenu(hostRef)
})

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
      load: () => hostApi.fetchHostOverview({ site_id: host.site_id, name: host.name })
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
            :tooltip="chip.tooltip"
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
          <ActionFeedback
            v-if="feedback"
            v-model:open="feedbackOpen"
            class="monitoring-all-hosts-app__feedback"
            :feedback="feedback"
          />
          <div class="monitoring-all-hosts-app__table-toolbar">
            <MonitoringActionBar
              v-if="hostActions.length > 0"
              class="monitoring-all-hosts-app__action-bar"
              :selected-count="selectedCount"
              :actions="hostActions"
              @action="onBulkAction"
            />
            <div class="monitoring-all-hosts-app__table-toolbar-end">
              <MonitoringTotalCount />
              <MonitoringLimitSelector />
              <ColumnPicker />
            </div>
          </div>
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
        <HostSlideInHeader
          v-if="slideInHost"
          :host="slideInHost"
          :actions="slideInInlineActions"
          :load-action-menu="slideInLoadActionMenu"
          @command="onRowCommand"
        />
      </template>
      <template #actions>
        <HostSlideInActions @select="openSlideInAction" />
      </template>
      <template #override>
        <CmkButton
          variant="optional"
          class="monitoring-all-hosts-app__slide-in-back"
          @click="closeSlideInAction"
        >
          <CmkIcon name="back" size="small" />
          {{ _t('Back to host detail view') }}
        </CmkButton>
        <MonitoringActionPane
          v-if="slideInActionId"
          :action-id="slideInActionId"
          :actions="actionRegistry"
          :targets="slideInTargets"
          indent
          :show-count="false"
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

.monitoring-all-hosts-app__feedback {
  flex: 0 0 auto;
  margin: 0 0 var(--spacing);
}

.monitoring-all-hosts-app__table-toolbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-bottom: var(--spacing);
}

.monitoring-all-hosts-app__action-bar {
  flex: 0 1 auto;
}

.monitoring-all-hosts-app__table-toolbar-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
  margin-left: auto;
}

.monitoring-all-hosts-app__table-toolbar-end > :not(:first-child) {
  border-left: 1px solid var(--font-color-dimmed);
  padding-left: var(--spacing);
}

.monitoring-all-hosts-app__slide-in-back {
  gap: var(--dimension-3);
  margin-bottom: var(--spacing);
}
</style>
