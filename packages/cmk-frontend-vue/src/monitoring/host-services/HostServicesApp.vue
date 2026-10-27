<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { useKeyboardHints } from 'cmk-ui-library/lib/keyboardHelp'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import { HostApi } from '@/monitoring/shared/api/hosts'
import type {
  HostEntry,
  HostOptionalField,
  HostRef,
  HostServiceEntry,
  ServiceRef
} from '@/monitoring/shared/api/types'
import DisplayOptionsPane from '@/monitoring/shared/components/DisplayOptionsPane.vue'
import HostHeader from '@/monitoring/shared/components/HostHeader.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import TypeToFocusIndicator from '@/monitoring/shared/components/TypeToFocusIndicator.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { sizeModeColumn, useModeColumnWidth } from '@/monitoring/shared/components/modeColumn'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import {
  displayOptionsWriter,
  readDisplayOptionsFromUrl,
  seedDisplayOptions
} from '@/monitoring/shared/displayOptionsState/urlState'
import { filterTimestampsAsShown } from '@/monitoring/shared/timestampFilters'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'

import HostSlideIn from '../all-hosts/components/HostSlideIn.vue'
import { HOST_TAB_OVERVIEW } from '../all-hosts/slideInTabs'
import { useHostActions } from '../all-hosts/useHostActions'
import MonitoringExportFeedback from '../shared/components/MonitoringExportFeedback.vue'
import MonitoringHeaderActions from '../shared/components/MonitoringHeaderActions.vue'
import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '../shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import MonitoringToolbar from '../shared/components/MonitoringToolbar.vue'
import { type ActionFeedback as ActionFeedbackResult } from '../shared/components/action/ActionFeedback.vue'
import { rowsToActOn } from '../shared/components/action/actions/remove'
import { RESCHEDULE_ACTION_ID } from '../shared/components/action/actions/reschedule'
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
import {
  IMMEDIATE_SERVICE_COMMAND_IDS,
  useServiceListing
} from '../shared/services/useServiceListing'
import { buildTableStateSchema } from '../shared/tableState/schema'
import { readTableStateFromUrl, tableStateWriter } from '../shared/tableState/urlState'
import {
  type SlideInListing,
  type SlideInUrlDescriptor,
  exactPattern,
  readSlideInFromHash,
  slideInWriter
} from '../shared/urlState/slideInState'
import { useUrlSync } from '../shared/urlState/useUrlSync'
import { useContextMenuKey } from '../shared/useContextMenuKey'
import { useFallbackKeys } from '../shared/useFallbackKeys'
import { useTypeToFocus } from '../shared/useTypeToFocus'
import { requestAiExplanation } from './aiExplain'
import { ServiceActionMenuApi } from './api/actionMenu'
import { HostServicesApi } from './api/services'
import {
  buildHostServicesColumnPinning,
  uncapNameWithoutSummary,
  useHostServicesColumns
} from './columns'
import HostServicesRow from './components/HostServicesRow.vue'
import ServiceSlideIn, { SERVICE_GRAPHS_TAB_ID } from './components/ServiceSlideIn.vue'
import { HostServicesService } from './services/HostServicesService'

const { _t } = usei18n()

useKeyboardHints(_t('Host services'), [
  ...tableKeyboardHints(),
  _t('Press [Enter] on a service name to open its details')
])

const props = defineProps<MonitoringHostServicesApp>()

const host: HostRef = { name: props.host, site_id: props.site }

const serviceListing = useServiceListing(props)

// Always-visible inline buttons (parameters). Their url keeps the {service} placeholder,
// resolved per row in HostServicesRow.
const rowActionButtons: CellAction[] = (props.row_actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: action.icon as SimpleIcons,
  url: action.url
}))

const actionMenuApi = new ServiceActionMenuApi()

// The legacy action-menu links (graphs, log file viewer, custom actions, ...), read when the
// menu is opened.
async function loadActionMenu(service: string): Promise<CellAction[]> {
  const items = await actionMenuApi.fetchActionMenu(host, service)
  return items.map((item) => ({
    id: `${item.title}|${item.url}`,
    label: item.title as TranslatedString,
    icon: item.icon_name as SimpleIcons,
    url: item.url,
    target: item.target,
    ident: item.ident
  }))
}

const hostActions = useHostActions({
  ...props,
  actions: props.host_actions,
  row_actions: props.host_row_actions
})

// What the host slide-in reads on the host of the page beyond what its header shows.
const hostFields: HostOptionalField[] = hostActions.rowActions.length > 0 ? ['setup_access'] : []

const aiExplain = props.ai_explain ?? false

const columns = useHostServicesColumns({
  includeSelect: serviceListing.mayActOnSelection,
  inlineActions: rowActionButtons.length + (aiExplain ? 1 : 0)
})
const columnPinning = buildHostServicesColumnPinning({
  includeSelect: serviceListing.mayActOnSelection
})

const schema = buildTableStateSchema({
  columns,
  limitTiers: props.limit_tiers,
  mayRemoveLimit: props.may_ignore_hard_limit ?? false
})
const initialState = readTableStateFromUrl(window.location.search, schema)

const filterSchema = buildFilterUrlSchema(columns)
const initialFilterState = readFilterUrlState(window.location.search, filterSchema)

const servicesApi = new HostServicesApi()
const hostApi = new HostApi()

const hostServicesService = new HostServicesService(
  servicesApi,
  hostApi,
  host,
  getKeyShortcutServiceInstance(),
  {
    pollIntervalMs: props.poll_interval_ms,
    tableStateSchema: schema,
    columnStorageKey: buildColumnStorageKey({
      view: 'host-services',
      site: props.site,
      userId: props.user_id,
      edition: props.edition
    }),
    columns,
    initialState,
    initialFilterState,
    quickFilters: serviceListing.quickFilters,
    hostFields
  }
)

const modeColumnSize = useModeColumnWidth(() => hostServicesService.items.value)
const initialDisplayOptions = readDisplayOptionsFromUrl(window.location.search)
const displayOptions = usePersistentRef(
  buildDisplayOptionsStorageKey({
    view: 'host-services',
    site: props.site,
    userId: props.user_id,
    edition: props.edition
  }),
  DEFAULT_DISPLAY_OPTIONS,
  (stored) => seedDisplayOptions(initialDisplayOptions, sanitizeDisplayOptions(stored))
)

const tableColumns = computed(() =>
  sizeModeColumn(
    filterTimestampsAsShown(
      uncapNameWithoutSummary(columns, hostServicesService.columnVisibility.value),
      displayOptions.value.timestampFormat
    ),
    modeColumnSize.value
  )
)

const toolbar = useTemplateRef<{ focus: () => void }>('toolbar')

const root = useTemplateRef<HTMLElement>('root')

const typeToFocus = useTypeToFocus(root)
useFallbackKeys(root, () => root.value?.querySelector<HTMLElement>('.monitoring-table'))
useContextMenuKey(root)

const instantReport = new InstantReport('report_instant_host_services.py')

function openInstantReport(): void {
  instantReport.open(
    hostServicesService.exportColumns(),
    servicesApi.requestBody(hostServicesService.listingParams()),
    { host: host.name, site: host.site_id }
  )
}

const exportFeedback = useRowExport(hostServicesService, {
  exportEvent: props.export_event,
  build: () => hostServicesService.export(),
  openReport: openInstantReport,
  texts: serviceListing.exportTexts
})

onMounted(() => {
  hostServicesService.onFocusSearch(() => toolbar.value?.focus())
})

onBeforeUnmount(() => {
  hostServicesService.destruct()
})

provide(MONITORING_SERVICE, hostServicesService)

function rowKey(row: HostServiceEntry): string {
  return row.name
}

const slideInService = ref<HostServiceEntry | null>(null)
const slideInTabId = ref<string | undefined>(undefined)
const slideInHost = ref<HostEntry | null>(null)
const slideInHostTabId = ref<string | undefined>(undefined)

function openSlideIn(service: HostServiceEntry): void {
  if (slideInService.value === null && slideInHost.value === null) {
    hostServicesService.beginAutoPause()
  }
  slideInHost.value = null
  slideInService.value = service
}

function openHostSlideIn(entry: HostEntry): void {
  if (slideInService.value === null && slideInHost.value === null) {
    hostServicesService.beginAutoPause()
  }
  slideInService.value = null
  slideInHost.value = entry
}

function closeHostSlideIn(): void {
  if (slideInHost.value !== null) {
    hostServicesService.endAutoPause()
  }
  slideInHost.value = null
}

function onHostTitleClick(event: MouseEvent): void {
  const entry = hostServicesService.hostEntry.value
  if (
    entry === null ||
    event.button !== 0 ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return
  }
  event.preventDefault()
  openHostSlideIn(entry)
}

function openServiceGraphs(service: HostServiceEntry): void {
  slideInTabId.value = SERVICE_GRAPHS_TAB_ID
  openSlideIn(service)
}

function closeSlideIn(): void {
  if (slideInService.value !== null) {
    hostServicesService.endAutoPause()
  }
  slideInService.value = null
}

// The host is the page, so a service needs nothing but its description to be
// named - unlike the all hosts listing, where the site has to come along. A
// service the listing does not show is fetched on its own, so a link to it opens
// whether or not the filter would have let it through.
const SERVICE_SLIDE_IN: SlideInUrlDescriptor<HostServiceEntry, string> = {
  keys: ['service'],
  defaultTabId: 'overview',
  encode: (service) => ({ service: service.name }),
  decode: (params) => {
    const name = params['service']
    return name === undefined || name === '' ? null : name
  },
  matches: (service, identity) => service.name === identity,
  load: async (identity) => {
    const response = await servicesApi.fetchServices(host, {
      filter: { type: 'condition', field: 'name', op: 'matches', value: exactPattern(identity) },
      limit: 1
    })
    return response.services.find((service) => service.name === identity) ?? null
  }
}

// The host is the page, so the only host this panel opens is the one it shows, named the way the
// all hosts listing names it. Its tab gets a key of its own, as the service panel owns `tab`.
const HOST_SLIDE_IN: SlideInUrlDescriptor<HostEntry, HostRef> = {
  keys: ['host', 'site'],
  tabKey: 'host_tab',
  defaultTabId: HOST_TAB_OVERVIEW,
  encode: (entry) => ({ host: entry.name, site: entry.site_id }),
  decode: (params) =>
    params['host'] === host.name && params['site'] === host.site_id ? host : null,
  matches: (entry, identity) => entry.name === identity.name && entry.site_id === identity.site_id,
  load: async (identity) =>
    hostApi.fetchHost(identity, undefined, hostFields.length > 0 ? hostFields : undefined)
}

const hostListing: SlideInListing<HostEntry> = {
  hasLoaded: hostServicesService.hasLoaded,
  items: computed(() => {
    const entry = hostServicesService.hostEntry.value
    return entry === null ? [] : [entry]
  }),
  revealRow: () => {}
}

useUrlSync([
  tableStateWriter(hostServicesService, schema),
  filterStateWriter(hostServicesService),
  displayOptionsWriter(displayOptions),
  slideInWriter({
    descriptor: SERVICE_SLIDE_IN,
    service: hostServicesService,
    current: slideInService,
    tabId: slideInTabId,
    initial: readSlideInFromHash(SERVICE_SLIDE_IN, window.location.hash),
    open: openSlideIn,
    close: closeSlideIn
  }),
  slideInWriter({
    descriptor: HOST_SLIDE_IN,
    service: hostListing,
    current: slideInHost,
    tabId: slideInHostTabId,
    initial: readSlideInFromHash(HOST_SLIDE_IN, window.location.hash),
    open: openHostSlideIn,
    close: closeHostSlideIn
  })
])

function serviceOfHost(description: string): ServiceRef {
  return { host, description }
}

function serviceRef(row: HostServiceEntry): ServiceRef {
  return serviceOfHost(row.name)
}

// As in the slide-in: a byproduct of the agent-based check reschedules the host's "Check_MK"
// service, and a service that cannot be rescheduled at all is left out.
function serviceActionTargets(rows: HostServiceEntry[], actionId: string): ServiceRef[] {
  if (actionId !== RESCHEDULE_ACTION_ID) {
    return rowsToActOn(rows, actionId).map(serviceRef)
  }
  return [...new Set(rows.flatMap((row) => row.reschedule?.target ?? []))].map(serviceOfHost)
}

function onServiceCommand(
  runCommand: (command: { id: string; target: ServiceRef }) => void,
  command: { id: string; target: string }
): void {
  runCommand({ id: command.id, target: serviceOfHost(command.target) })
}

function explainService(service: HostServiceEntry): void {
  const hostEntry = hostServicesService.hostEntry.value
  if (hostEntry === null) {
    return
  }
  requestAiExplanation({
    hostName: host.name,
    hostState: hostEntry.state,
    serviceName: service.name,
    serviceState: service.state,
    stale: service.stale
  })
}

function onActionPerformed(result: ActionFeedbackResult): void {
  if (result.variant === 'success') {
    hostServicesService.refresh(ACTION_REFRESH_DELAY_MS)
  }
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()
</script>

<template>
  <CmkErrorBoundary>
    <MonitoringHeaderActions :teleport-target="header_teleport_target">
      <MonitoringSurveyLink url="https://survey.checkmk.com/index.php/852195?lang=en" />
      <MonitoringLegacyViewButton
        v-if="legacy_view_button"
        :title="legacy_view_button.title"
        :url="legacy_view_button.url"
      />
    </MonitoringHeaderActions>
    <div ref="root" class="monitoring-host-services-app">
      <MonitoringToolbar
        ref="toolbar"
        :service="hostServicesService"
        :search-placeholder="_t('Search services…')"
      >
        <template v-if="hostServicesService.hostEntry.value" #subject>
          <HostHeader
            :host="hostServicesService.hostEntry.value"
            :url="host_url"
            @title-click="onHostTitleClick"
          />
        </template>
      </MonitoringToolbar>
      <MonitoringExportFeedback v-model="exportFeedback" />
      <MonitoringSplitPane
        :service="hostServicesService"
        :actions="serviceListing.registry"
        :bulk-actions="serviceListing.permittedActions"
        :more-actions="serviceListing.moreActions"
        :columns="tableColumns"
        :column-pinning="columnPinning"
        :get-row-key="rowKey"
        :get-action-target="serviceRef"
        :get-action-targets="serviceActionTargets"
        :immediate-action-ids="IMMEDIATE_SERVICE_COMMAND_IDS"
        :selection-label="serviceListing.selectionLabel"
        :actions-label="_t('Actions for selected services')"
        :counts-label="serviceListing.countsLabel"
        @performed="onActionPerformed"
      >
        <template #row="{ row, tableRow, onCommand }">
          <HostServicesRow
            :row="row"
            :table-row="tableRow"
            :row-actions="rowActionButtons"
            :may-reschedule="serviceListing.mayReschedule"
            :load-action-menu="loadActionMenu"
            :display-options="displayOptions"
            :ai-explain="aiExplain && hostServicesService.hostEntry.value !== null"
            @open="openSlideIn"
            @open-graphs="openServiceGraphs"
            @command="onServiceCommand(onCommand, $event)"
            @explain="explainService"
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
      <ServiceSlideIn
        v-model:active-tab-id="slideInTabId"
        :display-options="displayOptions"
        :service="slideInService"
        :host="host"
        :ai-explain="aiExplain"
        :actions="serviceListing.registry"
        :permitted-actions="serviceListing.permittedActions"
        :load-action-menu="loadActionMenu"
        @close="closeSlideIn"
        @performed="onActionPerformed"
      />
      <HostSlideIn
        v-model:active-tab-id="slideInHostTabId"
        :display-options="displayOptions"
        :host="slideInHost"
        :actions="hostActions.registry"
        :row-actions="hostActions.rowActions"
        :permitted-actions="hostActions.permittedActions"
        :load-action-menu="hostActions.loadActionMenu"
        @close="closeHostSlideIn"
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
.monitoring-host-services-app {
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
