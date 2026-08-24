<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import type { HostRef, HostServiceEntry, ServiceState } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import QuickFilterChip from '@/monitoring/shared/components/filter/QuickFilterChip.vue'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'

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
import {
  type SlideInUrlDescriptor,
  exactPattern,
  readSlideInFromHash,
  slideInWriter
} from '../shared/urlState/slideInState'
import { useUrlSync } from '../shared/urlState/useUrlSync'
import { useAcknowledgeServicesAction } from './actions/acknowledgeServices'
import { useRescheduleServicesAction } from './actions/rescheduleServices'
import { useScheduleServiceDowntimeAction } from './actions/scheduleServiceDowntime'
import { ServiceActionMenuApi } from './api/actionMenu'
import { HostServicesApi } from './api/services'
import { buildHostServicesColumnPinning, useHostServicesColumns } from './columns'
import HostServicesRow from './components/HostServicesRow.vue'
import ServiceSlideIn from './components/ServiceSlideIn.vue'
import { HostServicesService } from './services/HostServicesService'

const { _t, _tn } = usei18n()

const props = defineProps<MonitoringHostServicesApp>()

const host: HostRef = { name: props.host, site_id: props.site }

const serviceActions: CellAction[] = (props.actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: action.icon as SimpleIcons
}))

// Always-visible inline buttons (parameters). Their url keeps the {service} placeholder,
// resolved per row in HostServicesRow.
const rowActionButtons: CellAction[] = (props.row_actions ?? []).map((action) => ({
  id: action.ident,
  label: action.title as TranslatedString,
  icon: action.icon as SimpleIcons,
  url: action.url
}))

const actionMenuApi = new ServiceActionMenuApi()

// Command entries the row dropdown runs immediately with their default values, acting on that
// single service. Only actions that are safe without user input belong here — form-based ones
// (acknowledge, downtime) carry essential input and go through the action pane instead. They
// carry no url, so ActionsCell emits `select`.
const IMMEDIATE_ROW_COMMAND_IDS: readonly string[] = [RESCHEDULE_ACTION_ID]

const rowCommands: CellAction[] = serviceActions.filter((action) =>
  IMMEDIATE_ROW_COMMAND_IDS.includes(action.id)
)

// The immediate commands followed by the fetched legacy action-menu links (graphs, log file
// viewer, custom actions, ...), read when the menu is opened.
async function loadActionMenu(service: string): Promise<CellAction[]> {
  const items = await actionMenuApi.fetchActionMenu(host, service)
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

const columns = useHostServicesColumns()
const columnPinning = buildHostServicesColumnPinning()

const filterSchema = buildFilterUrlSchema(columns)
const initialFilterState = readFilterUrlState(window.location.search, filterSchema)

const servicesApi = new HostServicesApi()

const hostServicesService = new HostServicesService(
  servicesApi,
  host,
  getKeyShortcutServiceInstance(),
  {
    pollIntervalMs: props.poll_interval_ms,
    columnStorageKey: buildColumnStorageKey({
      view: 'host-services',
      site: props.site,
      userId: props.user_id,
      edition: props.edition
    }),
    columns,
    initialFilterState,
    quickFilters: [
      {
        label: _t('Unhandled service problems'),
        tooltip: _t(
          'Show only services in a problem state (WARN or CRIT) that are neither acknowledged nor in a scheduled downtime'
        ),
        filter: {
          type: 'and',
          children: [
            {
              type: 'condition',
              field: 'state',
              op: 'one_of',
              value: ['WARN', 'CRIT'] as ServiceState[]
            },
            { type: 'condition', field: 'acknowledged', op: 'eq', value: false },
            { type: 'condition', field: 'in_downtime', op: 'eq', value: false }
          ]
        }
      }
    ]
  }
)

const actionRegistry = createActionRegistry<string>([
  useAcknowledgeServicesAction(host),
  useRescheduleServicesAction(host),
  useScheduleServiceDowntimeAction(
    host,
    props.downtime_recurrences ?? [],
    props.downtime_presets_url ?? null
  )
])

const searchInput = useTemplateRef<{ focus: () => void }>('searchInput')

onMounted(() => {
  hostServicesService.onFocusSearch(() => searchInput.value?.focus())
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

function openSlideIn(service: HostServiceEntry): void {
  if (slideInService.value === null) {
    hostServicesService.beginAutoPause()
  }
  slideInService.value = service
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

useUrlSync([
  filterStateWriter(hostServicesService),
  slideInWriter({
    descriptor: SERVICE_SLIDE_IN,
    service: hostServicesService,
    current: slideInService,
    tabId: slideInTabId,
    initial: readSlideInFromHash(SERVICE_SLIDE_IN, window.location.hash),
    open: openSlideIn,
    close: closeSlideIn
  })
])

function serviceRef(row: HostServiceEntry): string {
  return row.name
}

function serviceSelectionLabel(count: number): TranslatedString {
  return _tn('%{count} service selected', '%{count} services selected', count, { count })
}

function serviceCountsLabel(selected: number, total: number): TranslatedString {
  return _tn(
    'Selected service: %{selected} | Total services: %{total}',
    'Selected services: %{selected} | Total services: %{total}',
    selected,
    { selected, total }
  )
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
    <MonitoringSurveyLink url="https://survey.checkmk.com/index.php/852195?lang=en" />
    <MonitoringLegacyViewButton
      v-if="legacy_view_button"
      :title="legacy_view_button.title"
      :url="legacy_view_button.url"
    />
    <div class="monitoring-host-services-app">
      <div class="monitoring-host-services-app__header">
        <div class="monitoring-host-services-app__toolbar">
          <CmkSearchInput
            ref="searchInput"
            v-model="hostServicesService.searchQuery.value"
            class="monitoring-host-services-app__search"
            :placeholder="_t('Search services…')"
            @search="hostServicesService.updateSearch($event)"
            @focusin="hostServicesService.beginAutoPause()"
            @focusout="hostServicesService.endAutoPause()"
          />
          <div class="monitoring-host-services-app__quick-filters">
            <QuickFilterChip
              v-for="chip in hostServicesService.filters.quickFilters"
              :key="chip.label"
              :label="chip.label"
              :tooltip="chip.tooltip"
              :active="chip.isActive.value"
              @activate="hostServicesService.activateQuickFilter(chip)"
              @deactivate="hostServicesService.deactivateQuickFilter(chip)"
            />
          </div>
          <CmkButton variant="text" size="small" @click="hostServicesService.clearAllFilters()">
            {{ _t('Reset all filters') }}
          </CmkButton>
        </div>
        <div class="monitoring-host-services-app__header-end">
          <RefreshCountdown
            :remaining="hostServicesService.secondsRemaining.value"
            :interval="hostServicesService.pollIntervalSeconds"
            :paused="hostServicesService.paused.value"
            :manual-paused="hostServicesService.manualPaused.value"
            size="small"
            @toggle="hostServicesService.togglePause()"
          />
        </div>
      </div>
      <MonitoringSplitPane
        :service="hostServicesService"
        :actions="actionRegistry"
        :bulk-actions="serviceActions"
        :columns="columns"
        :column-pinning="columnPinning"
        :get-row-key="rowKey"
        :get-action-target="serviceRef"
        :immediate-action-ids="IMMEDIATE_ROW_COMMAND_IDS"
        :selection-label="serviceSelectionLabel"
        :actions-label="_t('Actions for selected services')"
        :counts-label="serviceCountsLabel"
        @performed="onActionPerformed"
      >
        <template #row="{ row, tableRow, onCommand }">
          <HostServicesRow
            :row="row"
            :table-row="tableRow"
            :row-actions="rowActionButtons"
            :load-action-menu="loadActionMenu"
            @open="openSlideIn"
            @command="onCommand"
          />
        </template>
      </MonitoringSplitPane>
      <ServiceSlideIn
        v-model:active-tab-id="slideInTabId"
        :service="slideInService"
        :host="host"
        :ai-explain="props.ai_explain ?? false"
        :actions="actionRegistry"
        :permitted-actions="serviceActions"
        :load-action-menu="loadActionMenu"
        @close="closeSlideIn"
        @performed="onActionPerformed"
      />
    </div>
  </CmkErrorBoundary>
</template>

<style scoped>
.monitoring-host-services-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}

.monitoring-host-services-app__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
}

.monitoring-host-services-app__toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-services-app__header-end {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-services-app__search {
  flex: 1;
  max-width: 360px;
}

.monitoring-host-services-app__quick-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}
</style>
