<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'

import MetricsWizard from '../components/Wizard/MetricsWizard.vue'
import type { DashboardConstants } from '../types/dashboard'
import type { WidgetContent, WidgetFilterContext, WidgetGeneralSettings } from '../types/widget'

interface AllWizardsProps {
  selectedWizard: string
  dashboardConstants: DashboardConstants
  dashboardName: string
  dashboardOwner: string
  contextFilters: ContextFilters
}

const emit = defineEmits<{
  'back-button': []
  'add-widget': [
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
