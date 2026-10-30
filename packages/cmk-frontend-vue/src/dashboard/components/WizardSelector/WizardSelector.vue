<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideIn from 'cmk-ui-library/components/CmkSlideIn'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import type { DashboardFeatures, DashboardKey } from '../../types/dashboard.ts'
import type { ContextFilters } from '../../types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '../../types/widget'
import AlertsAndNotificationsWizard from '../Wizard/wizards/alert-notification/AlertNotificationWizard.vue'
import CloneCustomGraphWizard from '../Wizard/wizards/custom-graphs/CloneCustomGraphWizard.vue'
import CreateCustomGraphWizard from '../Wizard/wizards/custom-graphs/CreateCustomGraphWizard.vue'
import CustomGraphsWizard from '../Wizard/wizards/custom-graphs/CustomGraphsWizard.vue'
import EventsWizard from '../Wizard/wizards/events/EventsWizard.vue'
import HostsSiteWizard from '../Wizard/wizards/hosts-site/HostsSiteWizard.vue'
import HwSwInventoryWizard from '../Wizard/wizards/hw_sw_inventory/HwSwInventoryWizard.vue'
import MetricsWizard from '../Wizard/wizards/metrics/MetricsWizard.vue'
import MonitoringTableWizard from '../Wizard/wizards/monitoring-table/MonitoringTableWizard.vue'
import NtopWizard from '../Wizard/wizards/ntop/NtopWizard.vue'
import OtherWizard from '../Wizard/wizards/other/OtherWizard.vue'
import ServicesOverviewWizard from '../Wizard/wizards/services/ServicesOverviewWizard.vue'
import ViewWizardWrapper from '../Wizard/wizards/view/ViewWizardWrapper.vue'
import { wizardSlideInSize } from './utils'

interface AllWizardsProps {
  tick: number
  range: DateTimeRange
  isOpen: boolean
  selectedWizard: string
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
  editWidgetId: string | null
  dashboardFeatures: DashboardFeatures
  mayEditCustomGraph?: boolean
}

const { _t } = usei18n()

const emit = defineEmits<{
  'back-button': []
  'close-wizard': []
  'add-widget': [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
  'edit-widget': [
    widgetId: string,
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const props = defineProps<AllWizardsProps>()

// The graph of a linked widget the user switched to Clone, which replaces the Link wizard.
const linkedGraphToClone = ref<string | null>(null)
watch(
  () => [props.selectedWizard, props.isOpen],
  () => {
    linkedGraphToClone.value = null
  }
)
const activeWizard = computed(() =>
  linkedGraphToClone.value === null ? props.selectedWizard : 'clone_custom_graph'
)

const handleGoBack = () => {
  emit('back-button')
}

const handleClose = () => {
  emit('close-wizard')
}

const handleAddEditWidget = (
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) => {
  if (props.editWidgetId) {
    emit('edit-widget', props.editWidgetId, content, generalSettings, filterContext)
  } else {
    emit('add-widget', content, generalSettings, filterContext)
  }
}
</script>

<template>
  <div v-if="!selectedWizard"></div>
  <div v-else>
    <CmkSlideIn
      :open="isOpen"
      :aria-label="
        props.editWidgetId ? _t('Edit widget properties') : _t('Add widget to dashboard')
      "
      :size="wizardSlideInSize(activeWizard)"
    >
      <AlertsAndNotificationsWizard
        v-if="activeWizard === 'alerts_notifications'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <HostsSiteWizard
        v-if="activeWizard === 'host_site_overview'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :dashboard-features="dashboardFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <HwSwInventoryWizard
        v-if="activeWizard === 'hw_sw_inventory'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <MetricsWizard
        v-if="activeWizard === 'metrics_graphs'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :dashboard-features="dashboardFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <ServicesOverviewWizard
        v-if="activeWizard === 'service_overview'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :dashboard-features="dashboardFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <MonitoringTableWizard
        v-if="activeWizard === 'view'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <ViewWizardWrapper
        v-if="activeWizard === 'classic_view'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :edit-widget-id="editWidgetId"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <EventsWizard
        v-if="activeWizard === 'event_stats'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <CustomGraphsWizard
        v-if="activeWizard === 'link_custom_graph'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :may-edit-custom-graph="mayEditCustomGraph ?? false"
        @clone-graph="(name) => (linkedGraphToClone = name)"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <CreateCustomGraphWizard
        v-if="activeWizard === 'new_custom_graph'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <CloneCustomGraphWizard
        v-if="activeWizard === 'clone_custom_graph'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :linked-graph="linkedGraphToClone"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <OtherWizard
        v-if="activeWizard === 'other'"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <NtopWizard
        v-if="activeWizard === 'ntop'"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <!-- Other wizards can be added here similarly -->
    </CmkSlideIn>
  </div>
</template>
