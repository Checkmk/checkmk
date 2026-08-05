<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { MonitoringHostServicesApp } from 'cmk-shared-typing/typescript/monitoring/host_services'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import CmkSearchInput from 'cmk-ui-library/components/CmkSearchInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { getKeyShortcutServiceInstance } from 'cmk-ui-library/lib/keyShortcuts'
import { onBeforeUnmount, onMounted, provide, ref, useTemplateRef } from 'vue'

import type { HostRef, HostServiceEntry } from '@/monitoring/shared/api/types'
import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'

import MonitoringLegacyViewButton from '../shared/components/MonitoringLegacyViewButton.vue'
import MonitoringSplitPane from '../shared/components/MonitoringSplitPane.vue'
import MonitoringSurveyLink from '../shared/components/MonitoringSurveyLink.vue'
import RefreshCountdown from '../shared/components/RefreshCountdown.vue'
import { type ActionFeedback as ActionFeedbackResult } from '../shared/components/action/ActionFeedback.vue'
import { createActionRegistry } from '../shared/components/action/registry'
import { useScheduleServiceDowntimeAction } from './actions/scheduleServiceDowntime'
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

const columns = useHostServicesColumns()
const columnPinning = buildHostServicesColumnPinning()

const hostServicesService = new HostServicesService(
  new HostServicesApi(),
  host,
  getKeyShortcutServiceInstance(),
  {
    pollIntervalMs: props.poll_interval_ms,
    columns
  }
)

const actionRegistry = createActionRegistry<string>([useScheduleServiceDowntimeAction(host)])

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

function serviceRef(row: HostServiceEntry): string {
  return row.name
}

function serviceSelectionLabel(count: number): TranslatedString {
  return _tn('%{count} service selected', '%{count} services selected', count, { count })
}

function onActionPerformed(result: ActionFeedbackResult): void {
  if (result.variant === 'success') {
    hostServicesService.refresh(ACTION_REFRESH_DELAY_MS)
  }
}
</script>

<template>
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
      :selection-label="serviceSelectionLabel"
      :actions-label="_t('Actions for selected services')"
      @performed="onActionPerformed"
    >
      <template #row="{ row, tableRow }">
        <HostServicesRow :row="row" :table-row="tableRow" @open="openSlideIn" />
      </template>
    </MonitoringSplitPane>
    <ServiceSlideIn :service="slideInService" :host="host" @close="closeSlideIn" />
  </div>
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
</style>
