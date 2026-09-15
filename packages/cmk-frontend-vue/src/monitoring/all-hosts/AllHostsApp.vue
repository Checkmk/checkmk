<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import { HostApi } from '@/monitoring/shared/api/hosts'
import type { HostEntry, HostRef, HostState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { sizeModeColumn, useModeColumnWidth } from '@/monitoring/shared/components/modeColumn'
import { ACTION_REFRESH_DELAY_MS, HOST_LIMIT_TIERS } from '@/monitoring/shared/constants'

import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '../shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import MonitoringToolbar from '../shared/components/MonitoringToolbar.vue'
import { type ActionFeedback as ActionFeedbackResult } from '../shared/components/action/ActionFeedback.vue'
import { acknowledgeDefaults } from '../shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '../shared/components/action/actions/reschedule'
import { downtimePresets } from '../shared/components/action/actions/scheduleDowntime'
import { createActionRegistry } from '../shared/components/action/registry'
import { buildFilterUrlSchema } from '../shared/filterState/schema'
import { filterStateWriter, readFilterUrlState } from '../shared/filterState/urlState'
import { buildColumnStorageKey } from '../shared/services/MonitoringService'
import { buildTableStateSchema } from '../shared/tableState/schema'
import { readTableStateFromUrl, tableStateWriter } from '../shared/tableState/urlState'
import {
  type SlideInUrlDescriptor,
  readSlideInFromHash,
  slideInWriter
} from '../shared/urlState/slideInState'
import { useUrlSync } from '../shared/urlState/useUrlSync'
import { useAcknowledgeHostsAction } from './actions/acknowledgeHosts'
import { useRescheduleHostsAction } from './actions/rescheduleHosts'
import { useScheduleHostDowntimeAction } from './actions/scheduleHostDowntime'
import { HostActionMenuApi } from './api/actionMenu'
import { buildHostColumnPinning, buildHostColumns } from './columns'
import HostRow from './components/HostRow.vue'
import HostSlideIn from './components/HostSlideIn.vue'
import { HostService } from './services/HostService'
import { HOST_TAB_OVERVIEW } from './slideInTabs'

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

// Checkboxes only make sense where the selection can be acted on, so the permitted-action list
// that decides the action bar decides the select column too.
const mayActOnSelection = hostActions.length > 0

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

// Only hosts monitored by an edition with multi-tenancy support belong to a customer.
const showCustomer = props.edition === 'ultimatemt'

const columns = buildHostColumns({
  includeSelect: mayActOnSelection,
  includeActions: hasRowActions,
  showCustomer,
  sites: props.sites,
  showRelations: props.show_relations ?? false
})
const columnPinning = buildHostColumnPinning({
  includeSelect: mayActOnSelection,
  includeActions: hasRowActions
})

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

const modeColumnSize = useModeColumnWidth(() => hostService.items.value)
const tableColumns = computed(() => sizeModeColumn(columns, modeColumnSize.value))

const toolbar = useTemplateRef<{ focus: () => void }>('toolbar')

const actionRegistry = createActionRegistry([
  useAcknowledgeHostsAction(
    {
      presetsUrl: props.acknowledge_presets_url ?? null,
      notificationRulesUrl: props.notification_rules_url ?? null
    },
    acknowledgeDefaults(props.acknowledge_defaults)
  ),
  useRescheduleHostsAction(),
  useScheduleHostDowntimeAction(
    props.downtime_recurrences ?? [],
    downtimePresets(props.downtime_presets),
    props.downtime_presets_url ?? null
  )
])

onMounted(() => {
  hostService.onFocusSearch(() => toolbar.value?.focus())
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
// Counted rather than flagged: clicking the relation count of the host the panel already shows
// has to scroll there again, and a flag that is already set changes nothing.
const revealRelationsRequest = ref(0)

function openSlideIn(host: HostEntry, reveal: boolean = false): void {
  if (slideInHost.value === null) {
    hostService.beginAutoPause()
  }
  if (reveal) {
    slideInTabId.value = HOST_TAB_OVERVIEW
    revealRelationsRequest.value += 1
  } else {
    revealRelationsRequest.value = 0
  }
  slideInHost.value = host
}

function closeSlideIn(): void {
  if (slideInHost.value !== null) {
    hostService.endAutoPause()
  }
  slideInHost.value = null
}

function selectSlideInTab(id: string): void {
  slideInTabId.value = id
  if (id !== HOST_TAB_OVERVIEW) {
    revealRelationsRequest.value = 0
  }
}

// A host is identified by the site it lives on plus its name. The listing this
// URL describes usually carries that row already; when it does not - filtered
// out, or in a state it has since left - the panel is opened from a fetch of
// that one host instead, so a shared link keeps working.
const HOST_SLIDE_IN: SlideInUrlDescriptor<HostEntry, HostRef> = {
  keys: ['host', 'site'],
  defaultTabId: HOST_TAB_OVERVIEW,
  encode: (host) => ({ host: host.name, site: host.site_id }),
  decode: (params) => {
    const name = params['host']
    const siteId = params['site']
    return name === undefined || name === '' || siteId === undefined || siteId === ''
      ? null
      : { site_id: siteId, name }
  },
  matches: (host, identity) => host.name === identity.name && host.site_id === identity.site_id,
  load: async (identity) => hostApi.fetchHost(identity)
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
      <MonitoringToolbar
        ref="toolbar"
        :service="hostService"
        :search-placeholder="_t('Search hosts…')"
      />
      <MonitoringSplitPane
        :service="hostService"
        :actions="actionRegistry"
        :bulk-actions="hostActions"
        :columns="tableColumns"
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
        :active-tab-id="slideInTabId"
        :host="slideInHost"
        :reveal-relations-request="revealRelationsRequest"
        :actions="actionRegistry"
        :row-actions="rowActionButtons"
        :permitted-actions="hostActions"
        :load-action-menu="loadActionMenu"
        @update:active-tab-id="selectSlideInTab"
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
}
</style>
