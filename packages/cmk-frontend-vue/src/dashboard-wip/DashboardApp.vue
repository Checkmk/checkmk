<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, onBeforeMount, provide, ref } from 'vue'

import { randomId } from '@/lib/randomId'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'
import CmkIcon from '@/components/CmkIcon'

import DashboardComponent from '@/dashboard-wip/components/DashboardComponent.vue'
import DashboardFilterSettings from '@/dashboard-wip/components/DashboardFilterSettings/DashboardFilterSettings.vue'
import DashboardMenuHeader from '@/dashboard-wip/components/DashboardMenuHeader/DashboardMenuHeader.vue'
import { createWidgetLayout } from '@/dashboard-wip/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import AddWidgetDialog from '@/dashboard-wip/components/WidgetWorkflow/StarterDialog/AddWidgetDialog.vue'
import AddWidgetPage from '@/dashboard-wip/components/WidgetWorkflow/StarterPage/AddWidgetPage.vue'
import { dashboardWidgetWorkflows } from '@/dashboard-wip/components/WidgetWorkflow/WidgetWorkflowTypes'
import CloneDashboardWizard from '@/dashboard-wip/components/Wizard/CloneDashboardWizard.vue'
import CreateDashboardWizard from '@/dashboard-wip/components/Wizard/CreateDashboardWizard.vue'
import WizardSelector from '@/dashboard-wip/components/WizardSelector/WizardSelector.vue'
import { widgetTypeToSelectorMatcher } from '@/dashboard-wip/components/WizardSelector/utils.ts'
import type {
  ConfiguredFilters,
  FilterDefinition
} from '@/dashboard-wip/components/filter/types.ts'
import { useDashboardFilters } from '@/dashboard-wip/composables/useDashboardFilters.ts'
import { useDashboardWidgets } from '@/dashboard-wip/composables/useDashboardWidgets.ts'
import { useDashboardsManager } from '@/dashboard-wip/composables/useDashboardsManager.ts'
import {
  type ContentResponsiveGrid,
  type DashboardGeneralSettings,
  DashboardLayout,
  type DashboardMetadata,
  type DashboardModel
} from '@/dashboard-wip/types/dashboard.ts'
import { RuntimeFilterMode } from '@/dashboard-wip/types/filter.ts'
import type { DashboardPageProperties } from '@/dashboard-wip/types/page.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetLayout,
  WidgetSpec
} from '@/dashboard-wip/types/widget'
import { dashboardAPI, urlHandler } from '@/dashboard-wip/utils.ts'

import DashboardSettingsWizard from './components/Wizard/DashboardSettingsWizard.vue'

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const props = defineProps<DashboardPageProperties>()

const isDashboardEditingMode = ref(false)
const openDashboardFilterSettings = ref(false)
const openDashboardSettings = ref(false)
const openAddWidgetDialog = ref(false)
const openDashboardCreationDialog = ref(props.mode === 'create')
const openDashboardCloneDialog = ref(false)
const openWizard = ref(false)
const selectedWizard = ref('')
const widgetToEdit = ref<string | null>(null)

const filterCollection = ref<Record<string, FilterDefinition> | null>(null)
provide('filterCollection', filterCollection)

// So far, this is only needed and used by the DashboardContentNtop component
provide('urlParams', props.url_params)

const dashboardsManager = useDashboardsManager()

onBeforeMount(async () => {
  const filterResp = await dashboardAPI.listFilterCollection()
  const filterDefsRecord: Record<string, FilterDefinition> = {}
  filterResp.value.forEach((filter) => {
    filterDefsRecord[filter.id!] = filter
  })
  filterCollection.value = filterDefsRecord

  if (props.dashboard) {
    const dashboard = props.dashboard
    await dashboardsManager.loadDashboard(
      dashboard.name,
      dashboard.metadata.layout_type as DashboardLayout
    )
    dashboardFilters.handleApplyRuntimeFilters(dashboard.filter_context.context)
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

const handleGoBack = () => {
  openAddWidgetDialog.value = true
  openWizard.value = false
}

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
  openWizard.value = false
}

function editWidget(widgetId: string) {
  widgetToEdit.value = widgetId
  const widgetSpec = dashboardsManager.activeDashboard.value!.content.widgets[widgetId]
  if (!widgetSpec) {
    throw new Error(`Widget with id ${widgetId} not found`)
  }
  selectedWizard.value = widgetTypeToSelectorMatcher(widgetSpec.content.type)
  openWizard.value = true
}

function executeEditWidget(
  widgetId: string,
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) {
  // @TODO edit function
  // #dashboardWidgets.updateWidget(widgetId, content, generalSettings, filterContext)
  console.log('Edit widget', widgetId, content, generalSettings, filterContext)

  widgetToEdit.value = null
  openWizard.value = false
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
  await dashboardsManager.createDashboard(dashboardId, settings, layout, scopeIds, null)
  isDashboardEditingMode.value = true

  if (nextStep === 'setFilters') {
    openDashboardFilterSettings.value = true
  } else if (nextStep === 'viewList') {
    redirectToListDashboardsPage()
  } else {
    throw new Error(`Unknown next step: ${nextStep}`)
  }
}

const cloneDashboard = async (
  dashboardId: string,
  generalSettings: DashboardGeneralSettings,
  layout: DashboardLayout,
  nextStep: 'setFilters' | 'viewList'
) => {
  openDashboardCloneDialog.value = false
  if (layout === DashboardLayout.RELATIVE_GRID) {
    await dashboardAPI.cloneAsRelativeGridDashboard(
      dashboardsManager.activeDashboardName.value!,
      dashboardId,
      generalSettings
    )
  } else {
    await dashboardAPI.cloneAsResponsiveGridDashboard(
      dashboardsManager.activeDashboardName.value!,
      dashboardId,
      generalSettings
    )
  }
  if (nextStep === 'setFilters') {
    openDashboardFilterSettings.value = true
  } else if (nextStep === 'viewList') {
    redirectToListDashboardsPage()
  } else {
    throw new Error(`Unknown next step: ${nextStep}`)
  }
}

const redirectToListDashboardsPage = () => {
  window.location.href = props.links.list_dashboards
}

const handleApplyRuntimeFilters = (filters: ConfiguredFilters, mode: RuntimeFilterMode) => {
  dashboardFilters.handleApplyRuntimeFilters(filters)
  dashboardFilters.setRuntimeFiltersMode(mode)

  let urlSearchParams = {}
  if (Object.keys(filters).length > 0) {
    const allFilterIds: string[] = []
    const allFilterValues: Record<string, string> = {}
    Object.entries(filters).forEach(([filterId, filterValues]) => {
      Object.entries(filterValues).forEach(([key, value]) => {
        allFilterValues[key] = value
      })
      allFilterIds.push(filterId)
    })
    // TODO: may have to reverify after discussion on behavior
    urlSearchParams = {
      filled_in: 'filter',
      _apply: 'Apply+filters',
      ...(mode !== RuntimeFilterMode.MERGE ? { _active: allFilterIds.join(';') } : {}),
      ...allFilterValues
    }
  }

  const updatedDashboardUrl = urlHandler.updateWithPreserve(
    window.location.href,
    ['name'],
    urlSearchParams
  )
  urlHandler.updateCheckmkPageUrl(updatedDashboardUrl)
}

const updateDashboardSettings = async (
  dashboardName: string,
  generalSettings: DashboardGeneralSettings
) => {
  dashboardsManager.activeDashboard.value!.general_settings = generalSettings
  await dashboardsManager.persistDashboard()
  openDashboardSettings.value = false
  if (dashboardsManager.activeDashboardName.value !== dashboardName) {
    //TODO: Handle ID change
  }
}

function deepClone<T>(obj: T): T {
  return structuredClone(obj)
}
</script>

<template>
  <CmkErrorBoundary>
    <div>
      <DashboardMenuHeader
        :selected-dashboard="selectedDashboard"
        :link-user-guide="props.links.user_guide"
        :link-navigation-embedding-page="props.links.navigation_embedding_page"
        @open-filter="openDashboardFilterSettings = true"
        @open-settings="openDashboardSettings = true"
        @open-clone-workflow="openDashboardCloneDialog = true"
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
        :available-layouts="available_layouts"
        @create-dashboard="(...args) => createDashboard(...args)"
        @cancel-creation="redirectToListDashboardsPage"
      />
      <CloneDashboardWizard
        v-if="dashboardsManager.isInitialized.value"
        v-model:open="openDashboardCloneDialog"
        :active-dashboard-id="dashboardsManager.activeDashboardName.value || ''"
        :available-layouts="available_layouts"
        :reference-dashboard-general-settings="
          deepClone(dashboardsManager.activeDashboard.value!.general_settings)
        "
        :reference-dashboard-restricted-to-single="
          deepClone(
            dashboardsManager.activeDashboard.value!.filter_context.restricted_to_single || []
          )
        "
        :reference-dashboard-layout-type="
          dashboardsManager.activeDashboard.value!.content.layout.type as DashboardLayout
        "
        @clone-dashboard="(...args) => cloneDashboard(...args)"
        @cancel-clone="openDashboardCloneDialog = false"
      />
      <AddWidgetDialog
        v-model:open="openAddWidgetDialog"
        :workflow-items="dashboardWidgetWorkflows"
        @select="handleAddWidget"
        @close="openAddWidgetDialog = false"
      />
      <WizardSelector
        :is-open="openWizard"
        :selected-wizard="selectedWizard"
        :dashboard-name="dashboardsManager.activeDashboardName.value || ''"
        :dashboard-owner="dashboardsManager.activeDashboard.value?.owner || ''"
        :context-filters="dashboardFilters.contextFilters.value || {}"
        :dashboard-constants="dashboardsManager.constants.value!"
        :edit-widget-spec="getWidgetSpecToEdit(widgetToEdit ?? null)"
        :edit-widget-id="widgetToEdit"
        @back-button="handleGoBack"
        @add-widget="addWidget"
        @edit-widget="executeEditWidget"
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
        :configured-runtime-filters-mode="
          dashboardFilters.runtimeFiltersMode.value || RuntimeFilterMode.OVERRIDE
        "
        :can-edit="true"
        starting-tab="dashboard-filter"
        @save-dashboard-filters="dashboardFilters.handleSaveDashboardFilters"
        @apply-runtime-filters="handleApplyRuntimeFilters"
        @save-mandatory-runtime-filters="dashboardFilters.handleSaveMandatoryRuntimeFilters"
        @close="openDashboardFilterSettings = false"
      />
      <DashboardSettingsWizard
        v-if="openDashboardSettings"
        :active-dashboard-id="dashboardsManager.activeDashboardName.value!"
        :dashboard-general-settings="
          deepClone(dashboardsManager.activeDashboard.value!.general_settings)
        "
        :dashboard-restricted-to-single="
          dashboardsManager.activeDashboard.value!.filter_context.restricted_to_single!
        "
        @cancel="openDashboardSettings = false"
        @save="updateDashboardSettings"
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
      <AddWidgetPage
        v-if="Object.entries(dashboardWidgets.widgetCores.value).length === 0"
        :workflow-items="dashboardWidgetWorkflows"
        @select="handleAddWidget"
      />
    </template>
    <template v-else>
      <CmkIcon name="load-graph" size="xxlarge" />
    </template>
  </CmkErrorBoundary>
</template>
