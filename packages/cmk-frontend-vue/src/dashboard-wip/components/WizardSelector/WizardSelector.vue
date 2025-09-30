<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import MetricsWizard from '@/dashboard-wip/components/Wizard/MetricsWizard.vue'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

interface AllWizardsProps {
  selectedWizard: string
  dashboardConstants: DashboardConstants
  dashboardName: string
  dashboardOwner: string
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
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
</script>

<template>
  <div v-if="!props.selectedWizard"></div>
  <div v-else>
    <MetricsWizard
      v-if="props.selectedWizard === 'metrics_graphs'"
      :dashboard-name="props.dashboardName"
      :dashboard-constants="props.dashboardConstants"
      :context-filters="contextFilters"
      @go-back="handleGoBack"
      @add-widget="
        (content, generalSettings, filterContext) =>
          emit('add-widget', content, generalSettings, filterContext)
      "
    />
  </div>
</template>
