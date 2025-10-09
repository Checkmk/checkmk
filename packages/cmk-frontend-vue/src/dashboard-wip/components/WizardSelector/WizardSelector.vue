<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardConstants } from '../../types/dashboard.ts'
import type { ContextFilters } from '../../types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '../../types/widget'
import HostsSiteWizard from '../Wizard/wizards/hosts-site/HostsSiteWizard.vue'
import HwSwInventoryWizard from '../Wizard/wizards/hw_sw_inventory/HwSwInventoryWizard.vue'
import MetricsWizard from '../Wizard/wizards/metrics/MetricsWizard.vue'
import ServicesOverviewWizard from '../Wizard/wizards/services/ServicesOverviewWizard.vue'
import ViewWizard from '../Wizard/wizards/view/ViewWizard.vue'

interface AllWizardsProps {
  isOpen: boolean
  selectedWizard: string
  dashboardConstants: DashboardConstants
  dashboardName: string
  dashboardOwner: string
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
  editWidgetId: string | null
}

const emit = defineEmits<{
  'back-button': []
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
    <CmkSlideIn :open="isOpen">
      <HostsSiteWizard
        v-if="selectedWizard === 'host_site_overview'"
        :dashboard-name="dashboardName"
        :dashboard-constants="dashboardConstants"
        :context-filters="contextFilters"
        @go-back="handleGoBack"
        @add-widget="handleAddEditWidget"
      />

      <HwSwInventoryWizard
        v-if="selectedWizard === 'hw_sw_inventory'"
        :dashboard-name="dashboardName"
        :context-filters="contextFilters"
        :dashboard-constants="dashboardConstants"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @add-widget="handleAddEditWidget"
      />

      <MetricsWizard
        v-if="selectedWizard === 'metrics_graphs'"
        :dashboard-name="dashboardName"
        :dashboard-constants="dashboardConstants"
        :context-filters="contextFilters"
        @go-back="handleGoBack"
        @add-widget="handleAddEditWidget"
      />

      <ServicesOverviewWizard
        v-if="selectedWizard === 'service_overview'"
        :dashboard-name="dashboardName"
        :dashboard-constants="dashboardConstants"
        :context-filters="contextFilters"
        :edit-widget-spec="editWidgetSpec"
        @go-back="handleGoBack"
        @add-widget="handleAddEditWidget"
      />

      <ViewWizard
        v-if="selectedWizard === 'views'"
        :dashboard-name="dashboardName"
        :dashboard-owner="dashboardOwner"
        :dashboard-constants="dashboardConstants"
        :context-filters="contextFilters"
        @go-back="handleGoBack"
        @add-widget="handleAddEditWidget"
      />

      <!-- Other wizards can be added here similarly -->
    </CmkSlideIn>
  </div>
</template>
