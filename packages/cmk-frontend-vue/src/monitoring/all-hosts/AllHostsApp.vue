<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import type { HostEntry, HostRef, HostState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import { ACTION_REFRESH_DELAY_MS, HOST_LIMIT_TIERS } from '@/monitoring/shared/constants'

import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '../shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import RefreshCountdown from '../shared/components/RefreshCountdown.vue'
import { type ActionFeedback as ActionFeedbackResult } from '../shared/components/action/ActionFeedback.vue'
import { RESCHEDULE_ACTION_ID } from '../shared/components/action/actions/reschedule'
import { createActionRegistry } from '../shared/components/action/registry'
import { buildFilterUrlSchema } from '../shared/filterState/schema'
import { filterStateWriter, readFilterUrlState } from '../shared/filterState/urlState'
import { buildColumnStorageKey } from '../shared/services/MonitoringService'
import { buildTableStateSchema } from '../shared/tableState/schema'
import { readTableStateFromUrl, tableStateWriter } from '../shared/tableState/urlState'
import {
  type SlideInUrlDescriptor,
  exactPattern,
  readSlideInFromHash,
  slideInWriter
} from '../shared/urlState/slideInState'
import { useUrlSync } from '../shared/urlState/useUrlSync'
import { useAcknowledgeHostsAction } from './actions/acknowledgeHosts'
import { useRescheduleHostsAction } from './actions/rescheduleHosts'
import { useScheduleHostDowntimeAction } from './actions/scheduleHostDowntime'
import { HostActionMenuApi } from './api/actionMenu'
import { HostApi } from './api/hosts'
import { buildHostColumnPinning, buildHostColumns } from './columns'
import HostRow from './components/HostRow.vue'
import HostSlideIn from './components/HostSlideIn.vue'
import { HostService } from './services/HostService'

const { _t, _tn } = usei18n()

const props = defineProps<MonitoringAllHostsApp>()

// Icons come from the command registry. Only commands whose registry icon has no counterpart in the
// Vue icon set need an entry here.
const ACTION_ICON_OVERRIDES: Record<string, SimpleIcons> = {
  [RESCHEDULE_ACTION_ID]: 'reload'
}

const hostActions: CellAction[] = (props.actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: ACTION_ICON_OVERRIDES[action.ident] ?? (action.icon as SimpleIcons)
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
    icon: ACTION_ICON_OVERRIDES[action.ident] ?? (action.icon as SimpleIcons)
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

const columns = buildHostColumns({ includeActions: hasRowActions, sites: props.sites })
const columnPinning = buildHostColumnPinning({ includeActions: hasRowActions })

const schema = buildTableStateSchema({
  columns,
  limitTiers: HOST_LIMIT_TIERS,
  mayRemoveLimit: props.may_ignore_hard_limit ?? false
})
const initialState = readTableStateFromUrl(window.location.search, schema)

const filterSchema = buildFilterUrlSchema(columns)
const initialFilterState = readFilterUrlState(window.location.search, filterSchema)

const hostApi = new HostApi()

const hostService = new HostService(hostApi, getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms,
  tableStateSchema: schema,
  columnStorageKey: buildColumnStorageKey({
    view: 'all-hosts',
    site: props.site,
    userId: props.user_id,
    edition: props.edition
  }),
  columns,
  initialState,
  initialFilterState,
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

const actionRegistry = createActionRegistry([
  useAcknowledgeHostsAction(),
  useRescheduleHostsAction(),
  useScheduleHostDowntimeAction(props.downtime_recurrences ?? [])
])

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

function hostRef(row: HostEntry): HostRef {
  return { site_id: row.site_id, name: row.name }
}

function hostSelectionLabel(count: number): TranslatedString {
  return _tn('%{count} host selected', '%{count} hosts selected', count, { count })
}

function hostCountsLabel(selected: number, total: number): TranslatedString {
  return _tn(
    'Selected host: %{selected} | Total hosts: %{total}',
    'Selected hosts: %{selected} | Total hosts: %{total}',
    selected,
    { selected, total }
  )
}

const slideInHost = ref<HostEntry | null>(null)
const slideInTabId = ref<string | undefined>(undefined)

function openSlideIn(host: HostEntry): void {
  if (slideInHost.value === null) {
    hostService.beginAutoPause()
  }
  slideInHost.value = host
}

function closeSlideIn(): void {
  if (slideInHost.value !== null) {
    hostService.endAutoPause()
  }
  slideInHost.value = null
}

// A host is identified by the site it lives on plus its name. The listing this
// URL describes usually carries that row already; when it does not - filtered
// out, or in a state it has since left - the panel is opened from a fetch of
// that one host instead, so a shared link keeps working.
const HOST_SLIDE_IN: SlideInUrlDescriptor<HostEntry, HostRef> = {
  keys: ['host', 'site'],
  defaultTabId: 'overview',
  encode: (host) => ({ host: host.name, site: host.site_id }),
  decode: (params) => {
    const name = params['host']
    const siteId = params['site']
    return name === undefined || name === '' || siteId === undefined || siteId === ''
      ? null
      : { site_id: siteId, name }
  },
  matches: (host, identity) => host.name === identity.name && host.site_id === identity.site_id,
  load: async (identity) => {
    // `name` offers no equality operator, so an anchored pattern stands in for
    // one and the exact row is picked out of what comes back.
    const response = await hostApi.fetchHosts({
      filter: {
        type: 'and',
        children: [
          { type: 'condition', field: 'name', op: 'matches', value: exactPattern(identity.name) },
          { type: 'condition', field: 'site_id', op: 'one_of', value: [identity.site_id] }
        ]
      },
      limit: 1
    })
    return (
      response.hosts.find(
        (host) => host.name === identity.name && host.site_id === identity.site_id
      ) ?? null
    )
  }
}

useUrlSync([
  tableStateWriter(hostService, schema),
  filterStateWriter(hostService),
  slideInWriter({
    descriptor: HOST_SLIDE_IN,
    service: hostService,
    current: slideInHost,
    tabId: slideInTabId,
    initial: readSlideInFromHash(HOST_SLIDE_IN, window.location.hash),
    open: openSlideIn,
    close: closeSlideIn
  })
])

function onActionPerformed(result: ActionFeedbackResult): void {
  if (result.variant === 'success') {
    hostService.refresh(ACTION_REFRESH_DELAY_MS)
  }
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <CmkErrorBoundary>
    <MonitoringSurveyLink url="https://survey.checkmk.com/index.php/815511?lang=en" />
    <MonitoringLegacyViewButton
      v-if="legacy_view_button"
      :title="legacy_view_button.title"
      :url="legacy_view_button.url"
    />
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
          <CmkButton variant="text" size="small" @click="hostService.clearAllFilters()">
            {{ _t('Reset all filters') }}
          </CmkButton>
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
      <MonitoringSplitPane
        :service="hostService"
        :actions="actionRegistry"
        :bulk-actions="hostActions"
        :columns="columns"
        :column-pinning="columnPinning"
        :get-row-key="rowKey"
        :get-action-target="hostRef"
        :immediate-action-ids="IMMEDIATE_ROW_COMMAND_IDS"
        :selection-label="hostSelectionLabel"
        :actions-label="_t('Actions for selected hosts')"
        :counts-label="hostCountsLabel"
        @performed="onActionPerformed"
      >
        <template #row="{ row, tableRow, onCommand }">
          <HostRow
            :row="row"
            :table-row="tableRow"
            :row-actions="rowActionButtons"
            :load-action-menu="loadActionMenu"
            @open="openSlideIn"
            @command="onCommand"
          />
        </template>
      </MonitoringSplitPane>
      <HostSlideIn
        v-model:active-tab-id="slideInTabId"
        :host="slideInHost"
        :actions="actionRegistry"
        :row-actions="rowActionButtons"
        :permitted-actions="hostActions"
        :load-action-menu="loadActionMenu"
        @close="closeSlideIn"
        @performed="onActionPerformed"
      />
    </div>
  </CmkErrorBoundary>
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
</style>
