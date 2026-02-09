<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardFeatures, DashboardKey } from '../../types/dashboard.ts'
import type { ContextFilters } from '../../types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '../../types/widget'
import AlertsAndNotificationsWizard from '../Wizard/wizards/alert-notification/AlertNotificationWizard.vue'
import CustomGraphsWizard from '../Wizard/wizards/custom-graphs/CustomGraphsWizard.vue'
import EventsWizard from '../Wizard/wizards/events/EventsWizard.vue'
import HostsSiteWizard from '../Wizard/wizards/hosts-site/HostsSiteWizard.vue'
import HwSwInventoryWizard from '../Wizard/wizards/hw_sw_inventory/HwSwInventoryWizard.vue'
import MetricsWizard from '../Wizard/wizards/metrics/MetricsWizard.vue'
import OtherWizard from '../Wizard/wizards/other/OtherWizard.vue'
import ServicesOverviewWizard from '../Wizard/wizards/services/ServicesOverviewWizard.vue'
import ViewWizardWrapper from '../Wizard/wizards/view/ViewWizardWrapper.vue'

interface AllWizardsProps {
  isOpen: boolean
  selectedWizard: string
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
  editWidgetId: string | null
  availableFeatures: DashboardFeatures
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
      :size="selectedWizard === 'other' ? 'small' : 'medium'"
    >
      <AlertsAndNotificationsWizard
        v-if="selectedWizard === 'alerts_notifications'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <HostsSiteWizard
        v-if="selectedWizard === 'host_site_overview'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :available-features="availableFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <HwSwInventoryWizard
        v-if="selectedWizard === 'hw_sw_inventory'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <MetricsWizard
        v-if="selectedWizard === 'metrics_graphs'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :available-features="availableFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <ServicesOverviewWizard
        v-if="selectedWizard === 'service_overview'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :available-features="availableFeatures"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <ViewWizardWrapper
        v-if="selectedWizard === 'views'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        :edit-widget-id="editWidgetId"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <EventsWizard
        v-if="selectedWizard === 'event_stats'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <CustomGraphsWizard
        v-if="selectedWizard === 'custom_graphs'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <OtherWizard
        v-if="selectedWizard === 'other'"
        :dashboard-key="dashboardKey"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @close="handleClose"
        @add-widget="handleAddEditWidget"
      />

      <!-- Other wizards can be added here similarly -->
    </CmkSlideIn>
  </div>
</template>
