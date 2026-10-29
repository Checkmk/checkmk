<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringAllHostsApp } from 'cmk-shared-typing/typescript/monitoring/all_hosts'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { useKeyboardHints } from 'cmk-ui-library/lib/keyboardHelp'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import { HostApi } from '@/monitoring/shared/api/hosts'
import type { HostEntry, HostRef, HostState } from '@/monitoring/shared/api/types'
import DisplayOptionsPane from '@/monitoring/shared/components/DisplayOptionsPane.vue'
import HostSlideIn from '@/monitoring/shared/components/HostSlideIn.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import TypeToFocusIndicator from '@/monitoring/shared/components/TypeToFocusIndicator.vue'
import { sizeModeColumn, useModeColumnWidth } from '@/monitoring/shared/components/modeColumn'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import {
  displayOptionsWriter,
  readDisplayOptionsFromUrl,
  seedDisplayOptions
} from '@/monitoring/shared/displayOptionsState/urlState'
import { HOST_TAB_OVERVIEW } from '@/monitoring/shared/hostSlideInTabs'
import { labelCondition } from '@/monitoring/shared/labels'
import { filterTimestampsAsShown } from '@/monitoring/shared/timestampFilters'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'
import { IMMEDIATE_HOST_COMMAND_IDS, useHostActions } from '@/monitoring/shared/useHostActions'

import MonitoringExportFeedback from '../shared/components/MonitoringExportFeedback.vue'
import MonitoringHeaderActions from '../shared/components/MonitoringHeaderActions.vue'
import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '../shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import MonitoringToolbar from '../shared/components/MonitoringToolbar.vue'
import { type ActionFeedback as ActionFeedbackResult } from '../shared/components/action/ActionFeedback.vue'
import { rowsToActOn } from '../shared/components/action/actions/remove'
import { InstantReport } from '../shared/export/instantReport'
import { useRowExport } from '../shared/export/useRowExport'
import { buildFilterUrlSchema } from '../shared/filterState/schema'
import { filterStateWriter, readFilterUrlState } from '../shared/filterState/urlState'
import { tableKeyboardHints } from '../shared/keyboardHints'
import {
  buildColumnStorageKey,
  buildDisplayOptionsStorageKey,
  sanitizeDisplayOptions
} from '../shared/services/MonitoringService'
import { buildTableStateSchema } from '../shared/tableState/schema'
import { readTableStateFromUrl, tableStateWriter } from '../shared/tableState/urlState'
import {
  type SlideInUrlDescriptor,
  readSlideInFromHash,
  slideInWriter
} from '../shared/urlState/slideInState'
import { useUrlSync } from '../shared/urlState/useUrlSync'
import { useContextMenuKey } from '../shared/useContextMenuKey'
import { useFallbackKeys } from '../shared/useFallbackKeys'
import { useTypeToFocus } from '../shared/useTypeToFocus'
import { buildHostColumnPinning, buildHostColumns } from './columns'
import HostRow from './components/HostRow.vue'
import { HostService } from './services/HostService'

const { _t, _tn } = usei18n()

useKeyboardHints(_t('All hosts'), [
  ...tableKeyboardHints(),
  _t('Press [Enter] on a host name to open its details')
])

const props = defineProps<MonitoringAllHostsApp>()

const {
  permittedActions: hostActions,
  moreActions: moreHostActions,
  rowActions: rowActionButtons,
  registry: actionRegistry,
  loadActionMenu
} = useHostActions(props)

// Checkboxes only make sense where the selection can be acted on, so the permitted-action list
// that decides the action bar decides the select column too.
const mayActOnSelection = hostActions.length + moreHostActions.length > 0

// Only hosts monitored by an edition with multi-tenancy support belong to a customer.
const showCustomer = props.edition === 'ultimatemt'

const columns = buildHostColumns({
  includeSelect: mayActOnSelection,
  showCustomer,
  sites: props.sites,
  showRelations: props.show_relations ?? false
})
const columnPinning = buildHostColumnPinning({ includeSelect: mayActOnSelection })

const schema = buildTableStateSchema({
  columns,
  limitTiers: props.limit_tiers,
  mayRemoveLimit: props.may_ignore_hard_limit ?? false,
  // The page always sends its sort, so this is the order it lists in; the API's own default
  // only applies to callers that send none.
  defaultSort: [{ id: 'name', desc: false }]
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
  ],
  // Every row offers its graphs from the host name, whichever columns are shown.
  rowFields: ['graphs_link', ...(rowActionButtons.length > 0 ? (['setup_access'] as const) : [])]
})

const modeColumnSize = useModeColumnWidth(() => hostService.items.value)
const initialDisplayOptions = readDisplayOptionsFromUrl(window.location.search)
const displayOptions = usePersistentRef(
  buildDisplayOptionsStorageKey({
    view: 'all-hosts',
    site: props.site,
    userId: props.user_id,
    edition: props.edition
  }),
  DEFAULT_DISPLAY_OPTIONS,
  (stored) => seedDisplayOptions(initialDisplayOptions, sanitizeDisplayOptions(stored))
)

const tableColumns = computed(() =>
  sizeModeColumn(
    filterTimestampsAsShown(columns, displayOptions.value.timestampFormat),
    modeColumnSize.value
  )
)

const toolbar = useTemplateRef<{ focus: () => void }>('toolbar')

const root = useTemplateRef<HTMLElement>('root')

const typeToFocus = useTypeToFocus(root)
useFallbackKeys(root, () => root.value?.querySelector<HTMLElement>('.monitoring-table'))
useContextMenuKey(root)

const instantReport = new InstantReport('report_instant_all_hosts.py')

function openInstantReport(): void {
  instantReport.open(hostService.exportColumns(), hostApi.requestBody(hostService.listingParams()))
}

const exportFeedback = useRowExport(hostService, {
  exportEvent: props.export_event,
  build: () => hostService.export(),
  openReport: openInstantReport,
  texts: {
    exporting: _t('Exporting hosts…'),
    notLoaded: _t('The hosts could not be loaded, so nothing was exported.'),
    truncated: (counts, canShowMore) =>
      canShowMore
        ? _t('Exported %{exported} of %{matched} hosts. Show more hosts to export more.', counts)
        : _t(
            'Exported %{exported} of %{matched} hosts. Narrow the filters to export all of them.',
            counts
          )
  }
})

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

function hostActionTargets(rows: HostEntry[], actionId: string): HostRef[] {
  return rowsToActOn(rows, actionId).map(hostRef)
}

function hostSelectionLabel(count: number): TranslatedString {
  return _tn('Selected host: %{count}', 'Selected hosts: %{count}', count, { count })
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
  displayOptionsWriter(displayOptions),
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
    <MonitoringHeaderActions :teleport-target="header_teleport_target">
      <MonitoringSurveyLink url="https://survey.checkmk.com/index.php/815511?lang=en" />
      <MonitoringLegacyViewButton
        v-if="legacy_view_button"
        :title="legacy_view_button.title"
        :url="legacy_view_button.url"
      />
    </MonitoringHeaderActions>
    <div ref="root" class="monitoring-all-hosts-app">
      <MonitoringToolbar
        ref="toolbar"
        :service="hostService"
        :search-placeholder="_t('Search hosts…')"
      />
      <MonitoringExportFeedback v-model="exportFeedback" />
      <MonitoringSplitPane
        :service="hostService"
        :actions="actionRegistry"
        :bulk-actions="hostActions"
        :more-actions="moreHostActions"
        :columns="tableColumns"
        :column-pinning="columnPinning"
        :get-row-key="rowKey"
        :get-action-target="hostRef"
        :get-action-targets="hostActionTargets"
        :immediate-action-ids="IMMEDIATE_HOST_COMMAND_IDS"
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
            :display-options="displayOptions"
            @open="openSlideIn"
            @command="onCommand"
          />
        </template>
        <template #display-options="{ close }">
          <DisplayOptionsPane
            :model-value="displayOptions"
            @submit="
              (value) => {
                displayOptions = value
                close()
              }
            "
            @cancel="close"
          />
        </template>
      </MonitoringSplitPane>
      <HostSlideIn
        :display-options="displayOptions"
        :active-tab-id="slideInTabId"
        :host="slideInHost"
        :reveal-relations-request="revealRelationsRequest"
        :filter-labels-by="labelCondition"
        :actions="actionRegistry"
        :row-actions="rowActionButtons"
        :permitted-actions="hostActions"
        :load-action-menu="loadActionMenu"
        @update:active-tab-id="selectSlideInTab"
        @close="closeSlideIn"
        @performed="onActionPerformed"
      />
      <TypeToFocusIndicator
        :buffer="typeToFocus.buffer.value"
        :index="typeToFocus.index.value"
        :count="typeToFocus.count.value"
      />
    </div>
  </CmkErrorBoundary>
</template>

<style scoped>
.monitoring-all-hosts-app {
  position: relative;
  overflow-x: auto;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
}
</style>
