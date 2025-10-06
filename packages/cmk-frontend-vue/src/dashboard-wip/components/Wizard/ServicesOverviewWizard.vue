<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

import ServicesOverviewWizard from './wizards/services/ServicesOverviewWizard.vue'

interface ServicesOverviewWizardProps {
  dashboardName: string
  dashboardConstants: DashboardConstants
  contextFilters: ContextFilters

  editWidgetSpec?: WidgetSpec | null
}

defineProps<ServicesOverviewWizardProps>()

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
  updateWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const addWidget = (
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) => {
  emit('addWidget', content, generalSettings, filterContext)
}

const updateWidget = (
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) => {
  emit('updateWidget', content, generalSettings, filterContext)
}
</script>

<template>
  <CmkSlideIn :open="true">
    <ServicesOverviewWizard
      :dashboard-name="dashboardName"
      :context-filters="contextFilters"
      :dashboard-constants="dashboardConstants"
      :edit-widget-spec="editWidgetSpec ?? null"
      @go-back="() => emit('goBack')"
      @add-widget="addWidget"
      @update-widget="updateWidget"
    />
  </CmkSlideIn>
</template>
