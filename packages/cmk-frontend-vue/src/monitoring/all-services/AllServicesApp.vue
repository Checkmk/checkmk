<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringAllServicesApp } from 'cmk-shared-typing/typescript/monitoring/all_services'
import { useCmkErrorBoundary } from 'cmk-ui-library/components/CmkErrorBoundary'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { useKeyboardHints } from 'cmk-ui-library/lib/keyboardHelp'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { computed, onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import { ServiceActionMenuApi } from '@/monitoring/host-services/api/actionMenu'
import { uncapNameWithoutSummary } from '@/monitoring/host-services/columns'
import HostServicesRow from '@/monitoring/host-services/components/HostServicesRow.vue'
import ServiceSlideIn, {
  SERVICE_GRAPHS_TAB_ID
} from '@/monitoring/host-services/components/ServiceSlideIn.vue'
import type { HostRef, ServiceEntry, ServiceRef } from '@/monitoring/shared/api/types'
import DisplayOptionsPane from '@/monitoring/shared/components/DisplayOptionsPane.vue'
import MonitoringExportFeedback from '@/monitoring/shared/components/MonitoringExportFeedback.vue'
import MonitoringHeaderActions from '@/monitoring/shared/components/MonitoringHeaderActions.vue'
import MonitoringLegacyViewButton from '@/monitoring/shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '@/monitoring/shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '@/monitoring/shared/components/MonitoringSurveyLink.vue'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import MonitoringToolbar from '@/monitoring/shared/components/MonitoringToolbar.vue'
import TypeToFocusIndicator from '@/monitoring/shared/components/TypeToFocusIndicator.vue'
import { type ActionFeedback as ActionFeedbackResult } from '@/monitoring/shared/components/action/ActionFeedback.vue'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { sizeModeColumn, useModeColumnWidth } from '@/monitoring/shared/components/modeColumn'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import {
  displayOptionsWriter,
  readDisplayOptionsFromUrl,
  seedDisplayOptions
} from '@/monitoring/shared/displayOptionsState/urlState'
import { useRowExport } from '@/monitoring/shared/export/useRowExport'
import { buildFilterUrlSchema } from '@/monitoring/shared/filterState/schema'
import { filterStateWriter, readFilterUrlState } from '@/monitoring/shared/filterState/urlState'
import { tableKeyboardHints } from '@/monitoring/shared/keyboardHints'
import {
  buildColumnStorageKey,
  buildDisplayOptionsStorageKey,
  sanitizeDisplayOptions
} from '@/monitoring/shared/services/MonitoringService'
import {
  IMMEDIATE_SERVICE_COMMAND_IDS,
  useServiceListing
} from '@/monitoring/shared/services/useServiceListing'
import { buildTableStateSchema } from '@/monitoring/shared/tableState/schema'
import { readTableStateFromUrl, tableStateWriter } from '@/monitoring/shared/tableState/urlState'
import { filterTimestampsAsShown } from '@/monitoring/shared/timestampFilters'
import { DEFAULT_DISPLAY_OPTIONS } from '@/monitoring/shared/types'
import {
  type SlideInUrlDescriptor,
  exactPattern,
  readSlideInFromHash,
  slideInWriter
} from '@/monitoring/shared/urlState/slideInState'
import { useUrlSync } from '@/monitoring/shared/urlState/useUrlSync'
import { useContextMenuKey } from '@/monitoring/shared/useContextMenuKey'
import { useFallbackKeys } from '@/monitoring/shared/useFallbackKeys'
import { useTypeToFocus } from '@/monitoring/shared/useTypeToFocus'

import { AllServicesApi } from './api/services'
import { buildAllServicesColumnPinning, useAllServicesColumns } from './columns'
import { AllServicesService } from './services/AllServicesService'

const { _t } = usei18n()

useKeyboardHints(_t('All services'), [
  ...tableKeyboardHints(),
  _t('Press [Enter] on a service name to open its details')
])

const props = defineProps<MonitoringAllServicesApp>()

const serviceListing = useServiceListing(props)

const actionMenuApi = new ServiceActionMenuApi()

const aiExplain = props.ai_explain ?? false

function hostOf(service: ServiceEntry): HostRef {
  return { name: service.host_name, site_id: service.site_id }
}

async function loadActionMenu(host: HostRef, service: string): Promise<CellAction[]> {
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

const columns = useAllServicesColumns({
  includeSelect: serviceListing.mayActOnSelection,
  sites: props.sites
})
const columnPinning = buildAllServicesColumnPinning({
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

const servicesApi = new AllServicesApi()

const allServicesService = new AllServicesService(servicesApi, getKeyShortcutServiceInstance(), {
  pollIntervalMs: props.poll_interval_ms,
  tableStateSchema: schema,
  columnStorageKey: buildColumnStorageKey({
    view: 'all-services',
    site: props.site,
    userId: props.user_id,
    edition: props.edition
  }),
  columns,
  initialState,
  initialFilterState,
  quickFilters: serviceListing.quickFilters
})

const modeColumnSize = useModeColumnWidth(() => allServicesService.items.value)
const initialDisplayOptions = readDisplayOptionsFromUrl(window.location.search)
const displayOptions = usePersistentRef(
  buildDisplayOptionsStorageKey({
    view: 'all-services',
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
      uncapNameWithoutSummary(columns, allServicesService.columnVisibility.value),
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

const exportFeedback = useRowExport(allServicesService, {
  exportEvent: props.export_event,
  build: () => allServicesService.export(),
  texts: serviceListing.exportTexts
})

onMounted(() => {
  allServicesService.onFocusSearch(() => toolbar.value?.focus())
})

onBeforeUnmount(() => {
  allServicesService.destruct()
})

provide(MONITORING_SERVICE, allServicesService)

function rowKey(row: ServiceEntry): string {
  return JSON.stringify([row.site_id, row.host_name, row.name])
}

const slideInService = ref<ServiceEntry | null>(null)
const slideInTabId = ref<string | undefined>(undefined)
const NO_HOST: HostRef = { name: '', site_id: '' }
const slideInHost = computed<HostRef>(() =>
  slideInService.value === null ? NO_HOST : hostOf(slideInService.value)
)

function loadSlideInActionMenu(service: string): Promise<CellAction[]> {
  return loadActionMenu(slideInHost.value, service)
}

function openSlideIn(service: ServiceEntry): void {
  if (slideInService.value === null) {
    allServicesService.beginAutoPause()
  }
  slideInService.value = service
}

function openServiceGraphs(service: ServiceEntry): void {
  slideInTabId.value = SERVICE_GRAPHS_TAB_ID
  openSlideIn(service)
}

function closeSlideIn(): void {
  if (slideInService.value !== null) {
    allServicesService.endAutoPause()
  }
  slideInService.value = null
}

const SERVICE_SLIDE_IN: SlideInUrlDescriptor<ServiceEntry, ServiceRef> = {
  keys: ['host', 'site', 'service'],
  defaultTabId: 'overview',
  encode: (service) => ({ host: service.host_name, site: service.site_id, service: service.name }),
  decode: (params) => {
    const name = params['host']
    const siteId = params['site']
    const description = params['service']
    if (!name || !siteId || !description) {
      return null
    }
    return { host: { name, site_id: siteId }, description }
  },
  matches: (service, identity) =>
    service.name === identity.description &&
    service.host_name === identity.host.name &&
    service.site_id === identity.host.site_id,
  load: async (identity) => {
    const response = await servicesApi.fetchServices({
      filter: {
        type: 'and',
        children: [
          { type: 'condition', field: 'site_id', op: 'one_of', value: [identity.host.site_id] },
          {
            type: 'condition',
            field: 'host_name',
            op: 'matches',
            value: exactPattern(identity.host.name)
          },
          {
            type: 'condition',
            field: 'name',
            op: 'matches',
            value: exactPattern(identity.description)
          }
        ]
      },
      limit: 1
    })
    return response.services.find((service) => SERVICE_SLIDE_IN.matches(service, identity)) ?? null
  }
}

useUrlSync([
  tableStateWriter(allServicesService, schema),
  filterStateWriter(allServicesService),
  displayOptionsWriter(displayOptions),
  slideInWriter({
    descriptor: SERVICE_SLIDE_IN,
    service: allServicesService,
    current: slideInService,
    tabId: slideInTabId,
    initial: readSlideInFromHash(SERVICE_SLIDE_IN, window.location.hash),
    open: openSlideIn,
    close: closeSlideIn
  })
])

function serviceRef(row: ServiceEntry): ServiceRef {
  return { host: hostOf(row), description: row.name }
}

function serviceActionTargets(rows: ServiceEntry[], actionId: string): ServiceRef[] {
  if (actionId !== RESCHEDULE_ACTION_ID) {
    return rows.map(serviceRef)
  }
  const targets = new Map<string, ServiceRef>()
  for (const row of rows) {
    const description = row.reschedule?.target
    if (description !== undefined) {
      const target = { host: hostOf(row), description }
      targets.set(JSON.stringify([target.host.site_id, target.host.name, description]), target)
    }
  }
  return [...targets.values()]
}

function onActionPerformed(result: ActionFeedbackResult): void {
  if (result.variant === 'success') {
    allServicesService.refresh(ACTION_REFRESH_DELAY_MS)
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
    <div ref="root" class="monitoring-all-services-app">
      <MonitoringToolbar
        ref="toolbar"
        :service="allServicesService"
        :search-placeholder="_t('Search services…')"
      />
      <MonitoringExportFeedback v-model="exportFeedback" />
      <MonitoringSplitPane
        :service="allServicesService"
        :actions="serviceListing.registry"
        :bulk-actions="serviceListing.permittedActions"
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
            :may-reschedule="serviceListing.mayReschedule"
            :load-action-menu="(service: string) => loadActionMenu(hostOf(row), service)"
            :display-options="displayOptions"
            @open="openSlideIn(row)"
            @open-graphs="openServiceGraphs(row)"
            @command="
              (command) =>
                onCommand({
                  id: command.id,
                  target: { host: hostOf(row), description: command.target }
                })
            "
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
        :host="slideInHost"
        :ai-explain="aiExplain"
        :actions="serviceListing.registry"
        :permitted-actions="serviceListing.permittedActions"
        :load-action-menu="loadSlideInActionMenu"
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
.monitoring-all-services-app {
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
