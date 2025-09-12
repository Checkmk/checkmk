<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeMount, provide, ref } from 'vue'

import CmkIcon from '@/components/CmkIcon.vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'

import DashboardComponent from '@/dashboard-wip/components/DashboardComponent.vue'
import DashboardMenuHeader from '@/dashboard-wip/components/DashboardMenuHeader/DashboardMenuHeader.vue'
import AddWidgetDialog from '@/dashboard-wip/components/WidgetWorkflow/StarterDialog/AddWidgetDialog.vue'
import { dashboardWidgetWorkflows } from '@/dashboard-wip/components/WidgetWorkflow/WidgetWorkflowTypes.ts'
import type { FilterDefinition } from '@/dashboard-wip/components/filter/types.ts'
import { useDashboardFilters } from '@/dashboard-wip/composables/useDashboardFilters.ts'
import { useDashboardWidgets } from '@/dashboard-wip/composables/useDashboardWidgets.ts'
import { useDashboardsManager } from '@/dashboard-wip/composables/useDashboardsManager.ts'
import type { DashboardLayout, DashboardMetadata } from '@/dashboard-wip/types/dashboard.ts'
import type { DashboardPageProperties } from '@/dashboard-wip/types/page.ts'
import { dashboardAPI } from '@/dashboard-wip/utils.ts'

const { ErrorBoundary: errorBoundary } = useErrorBoundary()

const props = defineProps<DashboardPageProperties>()

const isDashboardEditingMode = ref(false)
const openDashboardFilterSettings = ref(false)
const openAddWidgetDialog = ref(false)

const filterCollection = ref<Record<string, FilterDefinition> | null>(null)
provide('filterCollection', filterCollection)

const dashboardsManager = useDashboardsManager()

onBeforeMount(async () => {
  const filterResp = await dashboardAPI.listFilterCollection()
  const filterDefsRecord: Record<string, FilterDefinition> = {}
  filterResp.value.forEach((filter) => {
    filterDefsRecord[filter.id!] = filter
  })
  filterCollection.value = filterDefsRecord

  if (props.dashboard) {
    await dashboardsManager.loadDashboard(
      props.dashboard.name,
      props.dashboard.metadata.layout_type as DashboardLayout
    )
  }
})

const dashboardFilters = useDashboardFilters(
  computed(() => dashboardsManager.activeDashboard.value?.filter_context)
)
const dashboardWidgets = useDashboardWidgets(
  computed(() => dashboardsManager.activeDashboard.value?.content.widgets)
)

const handleSelectDashboard = async (dashboard: DashboardMetadata) => {
  await dashboardsManager.loadDashboard(dashboard.name, dashboard.layout_type as DashboardLayout)
}

const selectedDashboard = computed(() => {
  if (!dashboardsManager.activeDashboard.value) {
    return null
  }

  return {
    name: dashboardsManager.activeDashboardName.value!,
    title: dashboardsManager.activeDashboard.value.general_settings.title.text
  }
})

const handleAddWidget = (_widgetIdent: string) => {
  openAddWidgetDialog.value = false

  // TODO: should be enabled for handling
  // selectedWizard.value = widgetIdent
  // openWizard.value = true
  // Logic to add the new widget to the dashboard goes here
  // The structure and composables already exist for this in useWidgets
}
</script>

<template>
  <errorBoundary>
    <div>
      <DashboardMenuHeader
        :selected-dashboard="selectedDashboard"
        @open-filter="openDashboardFilterSettings = true"
        @open-settings="() => {}"
        @open-widget-workflow="openAddWidgetDialog = true"
        @save="() => {}"
        @enter-edit="isDashboardEditingMode = true"
        @cancel-edit="() => {}"
        @set-dashboard="handleSelectDashboard"
      />
    </div>
    <div>
      <AddWidgetDialog
        v-model:open="openAddWidgetDialog"
        :workflow-items="dashboardWidgetWorkflows"
        @select="handleAddWidget"
        @close="openAddWidgetDialog = false"
      />
    </div>
    <template v-if="dashboardsManager.isInitialized.value">
      <DashboardComponent
        v-if="dashboardsManager.isInitialized.value"
        :key="`${dashboardsManager.activeDashboardName.value}`"
        v-model:dashboard="dashboardsManager.activeDashboard.value!"
        :dashboard-name="dashboardsManager.activeDashboardName.value || ''"
        :dashboard-owner="dashboardsManager.activeDashboard.value?.owner || ''"
        :base-filters="dashboardFilters.baseFilters"
        :widget-cores="dashboardWidgets.widgetCores"
        :constants="dashboardsManager.constants.value!"
        :is-editing="isDashboardEditingMode"
      />
    </template>
    <template v-else>
      <CmkIcon name="load-graph" size="xxlarge" />
    </template>
  </errorBoundary>
</template>
