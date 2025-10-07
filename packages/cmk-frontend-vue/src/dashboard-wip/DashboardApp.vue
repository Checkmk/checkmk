<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeMount, provide, ref } from 'vue'

import { randomId } from '@/lib/randomId'

import CmkIcon from '@/components/CmkIcon.vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'

import DashboardComponent from '@/dashboard-wip/components/DashboardComponent.vue'
import DashboardFilterSettings from '@/dashboard-wip/components/DashboardFilterSettings/DashboardFilterSettings.vue'
import DashboardMenuHeader from '@/dashboard-wip/components/DashboardMenuHeader/DashboardMenuHeader.vue'
import { createWidgetLayout } from '@/dashboard-wip/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import AddWidgetDialog from '@/dashboard-wip/components/WidgetWorkflow/StarterDialog/AddWidgetDialog.vue'
import { dashboardWidgetWorkflows } from '@/dashboard-wip/components/WidgetWorkflow/WidgetWorkflowTypes.ts'
import CreateDashboardWizard from '@/dashboard-wip/components/Wizard/CreateDashboardWizard.vue'
import WizardSelector from '@/dashboard-wip/components/WizardSelector/WizardSelector.vue'
import { widgetTypeToSelectorMatcher } from '@/dashboard-wip/components/WizardSelector/utils.ts'
import type { FilterDefinition } from '@/dashboard-wip/components/filter/types.ts'
import { useDashboardFilters } from '@/dashboard-wip/composables/useDashboardFilters.ts'
import { useDashboardWidgets } from '@/dashboard-wip/composables/useDashboardWidgets.ts'
import { useDashboardsManager } from '@/dashboard-wip/composables/useDashboardsManager.ts'
import type {
  ContentResponsiveGrid,
  DashboardGeneralSettings,
  DashboardLayout,
  DashboardMetadata,
  DashboardModel
} from '@/dashboard-wip/types/dashboard.ts'
import type { DashboardPageProperties } from '@/dashboard-wip/types/page.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetLayout,
  WidgetSpec
} from '@/dashboard-wip/types/widget'
import { dashboardAPI } from '@/dashboard-wip/utils.ts'

import DashboardSettingsWizard from './components/Wizard/DashboardSettingsWizard.vue'

const { ErrorBoundary: errorBoundary } = useErrorBoundary()

const props = defineProps<DashboardPageProperties>()

const isDashboardEditingMode = ref(false)
const openDashboardFilterSettings = ref(false)
const openDashboardSettings = ref(false)
const openAddWidgetDialog = ref(false)
const openDashboardCreationDialog = ref(props.mode === 'create')
const openWizard = ref(false)
const selectedWizard = ref('')
const widgetToEdit = ref<string | null>(null)

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

const handleAddWidget = (widgetIdent: string) => {
  openAddWidgetDialog.value = false
  selectedWizard.value = widgetIdent
  openWizard.value = true

  // TODO: should be enabled for handling
  // Logic to add the new widget to the dashboard goes here
  // The structure and composables already exist for this in useWidgets
  // TODO: better handling for cancelling
}

function generateWidgetId(widgetContentType: string): string {
  const dashboardName = dashboardsManager.activeDashboardName.value
  if (!dashboardName) {
    throw new Error('No active dashboard')
  }
  return randomId(16, `${dashboardName}-${widgetContentType}`)
}

async function saveDashboard() {
  await dashboardsManager.persistDashboard()
  isDashboardEditingMode.value = false
}

async function cancelEdit() {
  // we overwrite all changes by reloading the dashboard
  await dashboardsManager.loadDashboard(
    dashboardsManager.activeDashboardName.value!,
    dashboardsManager.activeDashboard.value!.content.layout.type as DashboardLayout
  )
  isDashboardEditingMode.value = false
}

// @ts-expect-error: TODO: use this
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function addWidget(
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) {
  const activeDashboard = dashboardsManager.activeDashboard.value as DashboardModel
  if (!activeDashboard) {
    throw new Error('No active dashboard')
  }
  const widgetId = generateWidgetId(content.type)
  let layout: WidgetLayout
  if (activeDashboard.content.layout.type === 'responsive_grid') {
    layout = createWidgetLayout(activeDashboard.content as ContentResponsiveGrid, content.type)
  } else if (activeDashboard.content.layout.type === 'relative_grid') {
    const widgetConstants = dashboardsManager.constants.value!.widgets[content.type]!
    layout = {
      type: 'relative_grid',
      position: widgetConstants.layout.relative.initial_position,
      size: widgetConstants.layout.relative.initial_size
    }
  } else {
    throw new Error(`Unknown dashboard layout type: ${activeDashboard.content.layout}`)
  }
  dashboardWidgets.addWidget(widgetId, content, generalSettings, filterContext, layout)
}

function editWidget(widgetId: string) {
  widgetToEdit.value = widgetId
  const widgetSpec = dashboardsManager.activeDashboard.value!.content.widgets[widgetId]
  if (!widgetSpec) {
    throw new Error(`Widget with id ${widgetId} not found`)
  }
  selectedWizard.value = widgetTypeToSelectorMatcher(widgetSpec.content.type)
}

function cloneWidget(oldWidgetId: string, newLayout: WidgetLayout) {
  const oldWidget = dashboardWidgets.getWidget(oldWidgetId)
  if (!oldWidget) {
    throw new Error(`Widget with id ${oldWidgetId} not found`)
  }
  const newWidgetId = generateWidgetId(oldWidget.content.type)
  dashboardWidgets.cloneWidget(oldWidgetId, newWidgetId, newLayout)
}

function getWidgetSpecToEdit(widgetId: string | null): WidgetSpec | null {
  if (!widgetId) {
    return null
  }
  const widget = dashboardsManager.activeDashboard.value!.content.widgets[widgetId]
  if (!widget) {
    throw new Error(`Widget with id ${widgetId} not found`)
  }
  return {
    content: widget.content,
    general_settings: widget.general_settings,
    filter_context: widget.filter_context
  }
}

const createDashboard = async (
  dashboardId: string,
  settings: DashboardGeneralSettings,
  layout: DashboardLayout,
  scopeIds: string[],
  nextStep: 'setFilters' | 'viewList'
) => {
  openDashboardCreationDialog.value = false
  await dashboardsManager.createDashboard(dashboardId, settings, layout, scopeIds)
  isDashboardEditingMode.value = true

  if (nextStep === 'setFilters') {
    openDashboardFilterSettings.value = true
  } else if (nextStep === 'viewList') {
    // TODO
    console.log('return to list review')
  } else {
    throw new Error(`Unknown next step: ${nextStep}`)
  }
}

function deepClone<T>(obj: T): T {
  return structuredClone(obj)
}
</script>

<template>
  <errorBoundary>
    <div>
      <DashboardMenuHeader
        :selected-dashboard="selectedDashboard"
        @open-filter="openDashboardFilterSettings = true"
        @open-settings="openDashboardSettings = true"
        @open-widget-workflow="openAddWidgetDialog = true"
        @save="saveDashboard"
        @enter-edit="isDashboardEditingMode = true"
        @cancel-edit="cancelEdit"
        @set-dashboard="handleSelectDashboard"
      />
    </div>
    <div>
      <CreateDashboardWizard
        v-model:open="openDashboardCreationDialog"
        @create-dashboard="(...args) => createDashboard(...args)"
      />
      <AddWidgetDialog
        v-model:open="openAddWidgetDialog"
        :workflow-items="dashboardWidgetWorkflows"
        @select="handleAddWidget"
        @close="openAddWidgetDialog = false"
      />
      <WizardSelector
        :selected-wizard="selectedWizard"
        :dashboard-name="dashboardsManager.activeDashboardName.value || ''"
        :dashboard-owner="dashboardsManager.activeDashboard.value?.owner || ''"
        :context-filters="dashboardFilters.contextFilters.value || {}"
        :dashboard-constants="dashboardsManager.constants.value!"
        :edit-widget-spec="getWidgetSpecToEdit(widgetToEdit)"
        @back-button="openAddWidgetDialog = true"
      />
      <DashboardFilterSettings
        v-model:open="openDashboardFilterSettings"
        :configured-dashboard-filters="
          deepClone(dashboardFilters.configuredDashboardFilters.value || {})
        "
        :applied-runtime-filters="deepClone(dashboardFilters.appliedRuntimeFilters.value || {})"
        :configured-mandatory-runtime-filters="[
          ...(dashboardFilters.configuredMandatoryRuntimeFilters.value || [])
        ]"
        :can-edit="true"
        starting-tab="dashboard-filter"
        @save-dashboard-filters="dashboardFilters.handleSaveDashboardFilters"
        @apply-runtime-filters="dashboardFilters.handleApplyRuntimeFilters"
        @save-mandatory-runtime-filters="dashboardFilters.handleSaveMandatoryRuntimeFilters"
        @close="openDashboardFilterSettings = false"
      />
      <DashboardSettingsWizard
        v-if="openDashboardSettings"
        :dashboard-id="dashboardsManager.activeDashboardName.value!"
        :dashboard-general-settings="
          deepClone(dashboardsManager.activeDashboard.value!.general_settings)
        "
        :dashboard-restricted-to-single="
          dashboardsManager.activeDashboard.value!.filter_context.restricted_to_single!
        "
        @cancel="openDashboardSettings = false"
        @save="() => {}"
      />
    </div>
    <template v-if="dashboardsManager.isInitialized.value">
      <DashboardComponent
        v-if="dashboardsManager.isInitialized.value"
        :key="`${dashboardsManager.activeDashboardName.value}`"
        v-model:dashboard="dashboardsManager.activeDashboard.value!"
        :dashboard-name="dashboardsManager.activeDashboardName.value || ''"
        :base-filters="dashboardFilters.baseFilters"
        :widget-cores="dashboardWidgets.widgetCores"
        :constants="dashboardsManager.constants.value!"
        :is-editing="isDashboardEditingMode"
        @widget:edit="editWidget($event)"
        @widget:delete="dashboardWidgets.deleteWidget($event)"
        @widget:clone="(oldWidgetId, newLayout) => cloneWidget(oldWidgetId, newLayout)"
      />
    </template>
    <template v-else>
      <CmkIcon name="load-graph" size="xxlarge" />
    </template>
  </errorBoundary>
</template>
