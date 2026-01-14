<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, onBeforeMount, provide, ref, watch } from 'vue'

import { randomId } from '@/lib/randomId'

import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'
import CmkIcon from '@/components/CmkIcon'

import DashboardBreadcrumb from '@/dashboard/components/DashboardBreadcrumb/DashboardBreadcrumb.vue'
import DashboardComponent from '@/dashboard/components/DashboardComponent.vue'
import DashboardFilterSettings from '@/dashboard/components/DashboardFilterSettings/DashboardFilterSettings.vue'
import DashboardMenuHeader from '@/dashboard/components/DashboardMenuHeader/DashboardMenuHeader.vue'
import type { SelectedDashboard } from '@/dashboard/components/DashboardMenuHeader/types'
import { createWidgetLayout } from '@/dashboard/components/ResponsiveGrid/composables/useResponsiveGridLayout'
import AddWidgetDialog from '@/dashboard/components/WidgetWorkflow/StarterDialog/AddWidgetDialog.vue'
import AddWidgetPage from '@/dashboard/components/WidgetWorkflow/StarterPage/AddWidgetPage.vue'
import { dashboardWidgetWorkflows } from '@/dashboard/components/WidgetWorkflow/WidgetWorkflowTypes'
import CloneDashboardWizard from '@/dashboard/components/Wizard/CloneDashboardWizard.vue'
import CreateDashboardWizard from '@/dashboard/components/Wizard/CreateDashboardWizard.vue'
import WizardSelector from '@/dashboard/components/WizardSelector/WizardSelector.vue'
import { widgetTypeToSelectorMatcher } from '@/dashboard/components/WizardSelector/utils.ts'
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard/components/filter/types.ts'
import { useDashboardFilters } from '@/dashboard/composables/useDashboardFilters.ts'
import { useDashboardWidgets } from '@/dashboard/composables/useDashboardWidgets.ts'
import { useDashboardsManager } from '@/dashboard/composables/useDashboardsManager.ts'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction.ts'
import { useProvideVisualInfos } from '@/dashboard/composables/useProvideVisualInfos'
import { useComputeWidgetTitles } from '@/dashboard/composables/useWidgetTitles'
import {
  type ContentResponsiveGrid,
  type DashboardGeneralSettings,
  type DashboardKey,
  DashboardLayout,
  type DashboardMetadata,
  type DashboardModel
} from '@/dashboard/types/dashboard.ts'
import { RuntimeFilterMode } from '@/dashboard/types/filter.ts'
import { urlParamsKey } from '@/dashboard/types/injectionKeys.ts'
import type { BreadcrumbItem } from '@/dashboard/types/page'
import type { DashboardPageProperties } from '@/dashboard/types/page.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetLayout,
  WidgetSpec
} from '@/dashboard/types/widget'
import { dashboardAPI, urlHandler } from '@/dashboard/utils.ts'

import DashboardSettingsWizard from './components/Wizard/DashboardSettingsWizard.vue'
import DashboardSharingWizard from './components/Wizard/wizards/dashboard-sharing/DashboardSharingWizard.vue'

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const props = defineProps<DashboardPageProperties>()

const isDashboardLoading = ref(false)
const isDashboardEditingMode = ref(props.mode === 'edit_layout')
const openDashboardFilterSettings = ref(false)
const openDashboardSettings = ref(props.mode === 'edit_settings')
const openAddWidgetDialog = ref(false)
const openDashboardCreationDialog = ref(props.mode === 'create')
const openDashboardCloneDialog = ref(props.mode === 'clone')
const isCloning = ref(false)
const openDashboardShareDialog = ref(false)
const openWizard = ref(false)
const selectedWizard = ref('')
const widgetToEdit = ref<string | null>(null)
const selectedDashboardBreadcrumb = ref<BreadcrumbItem[] | null>(null)

const dashboardFilterSettingsStartingWindow = ref<'runtime-filters' | 'filter-configuration'>(
  'runtime-filters'
)

const filterCollection = ref<Record<string, FilterDefinition> | null>(null)
provide('filterCollection', filterCollection)

useProvideVisualInfos()

// So far, this is only needed and used by the DashboardContentNtop component
provide(urlParamsKey, props.url_params)

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
    const key: DashboardKey = {
      name: dashboard.metadata.name,
      owner: dashboard.metadata.owner || '' // built-in conversion: null -> ""
    }
    isDashboardLoading.value = true
    try {
      await dashboardsManager.loadDashboard(key, dashboard.metadata.layout_type as DashboardLayout)
    } finally {
      isDashboardLoading.value = false
    }
    dashboardFilters.handleApplyRuntimeFilters(dashboard.filter_context.context)
    if (!dashboardFilters.areAllMandatoryFiltersApplied.value) {
      openDashboardFilterSettings.value = true
    }
  }
})

const dashboardFilters = useDashboardFilters(
  computed(() => dashboardsManager.activeDashboard.value?.model.filter_context)
)
const dashboardWidgets = useDashboardWidgets(
  computed(() => dashboardsManager.activeDashboard.value?.model.content.widgets)
)
const widgetTitles = useComputeWidgetTitles(
  dashboardFilters.baseFilters,
  dashboardWidgets.widgetCores
)

useProvideMissingRuntimeFiltersAction(dashboardFilters.areAllMandatoryFiltersApplied, () => {
  openDashboardFilterSettings.value = true
})

watch(dashboardsManager.activeDashboard, (value) => {
  selectedDashboardBreadcrumb.value = value?.metadata.display.topic.breadcrumb ?? null
})

const setAsActiveDashboard = async (dashboardKey: DashboardKey, layout: DashboardLayout) => {
  isDashboardLoading.value = true
  try {
    await dashboardsManager.loadDashboard(dashboardKey, layout)
  } finally {
    isDashboardLoading.value = false
  }

  const updatedDashboardUrl = urlHandler.getDashboardUrl(
    dashboardKey,
    dashboardFilters.getRuntimeFiltersSearchParams()
  )
  urlHandler.updateCurrentUrl(updatedDashboardUrl)
}

const handleSelectDashboard = async (dashboard: DashboardMetadata) => {
  const key: DashboardKey = {
    name: dashboard.name,
    owner: dashboard.owner || '' // built-in conversion: null -> ""
  }
  await setAsActiveDashboard(key, dashboard.layout_type as DashboardLayout)

  if (!dashboardFilters.areAllMandatoryFiltersApplied.value) {
    openDashboardFilterSettings.value = true
  }
}

const selectedDashboard = computed(() => {
  if (!dashboardsManager.activeDashboard.value) {
    return null
  }

  return {
    name: dashboardsManager.activeDashboardKey.value!.name,
    owner: dashboardsManager.activeDashboardKey.value!.owner,
    title: dashboardsManager.activeDashboard.value.model.general_settings.title.text,
    type: dashboardsManager.activeDashboard.value.model.type
  } as SelectedDashboard
})

const handleWizardSelectorGoBack = () => {
  // when editing, do not go back to widget type selection (and clear the edit state)
  if (widgetToEdit.value) {
    widgetToEdit.value = null
  } else {
    openAddWidgetDialog.value = true
  }
  openWizard.value = false
}

const handleAddWidget = (widgetIdent: string) => {
  openAddWidgetDialog.value = false
  selectedWizard.value = widgetIdent
  openWizard.value = true
  // TODO: better handling for cancelling
}

function generateWidgetId(widgetContentType: string): string {
  const key = dashboardsManager.activeDashboardKey.value
  if (!key) {
    throw new Error('No active dashboard')
  }
  return randomId(16, `${key.name}-${widgetContentType}`)
}

async function saveDashboard() {
  await dashboardsManager.persistDashboard()
  isDashboardEditingMode.value = false
}

async function cancelEdit() {
  // we overwrite all changes by reloading the dashboard
  isDashboardLoading.value = true
  try {
    await dashboardsManager.loadDashboard(
      dashboardsManager.activeDashboardKey.value!,
      dashboardsManager.activeDashboard.value!.model.content.layout.type as DashboardLayout
    )
  } finally {
    isDashboardLoading.value = false
  }
  isDashboardEditingMode.value = false
}

function addWidget(
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) {
  const activeDashboard = dashboardsManager.activeDashboard.value?.model as DashboardModel
  if (!activeDashboard) {
    throw new Error('No active dashboard')
  }
  const widgetId = generateWidgetId(content.type)
  let layout: WidgetLayout
  if (activeDashboard.content.layout.type === 'responsive_grid') {
    layout = createWidgetLayout(
      activeDashboard.content as ContentResponsiveGrid,
      content.type,
      dashboardsManager.constants.value!.responsive_grid_breakpoints
    )
  } else if (activeDashboard.content.layout.type === 'relative_grid') {
    const widgetConstants = dashboardsManager.constants.value!.widgets[content.type]!
    // Add a static vertical offset to reduce the chance of placing the new widget in a way where it covers existing
    // widgets
    const yOffset = Object.keys(dashboardWidgets.widgetCores.value).length > 0 ? 5 : 0
    layout = {
      type: 'relative_grid',
      position: {
        x: widgetConstants.layout.relative.initial_position.x,
        y: widgetConstants.layout.relative.initial_position.y + yOffset
      },
      size: widgetConstants.layout.relative.initial_size
    }
  } else {
    throw new Error(`Unknown dashboard layout type: ${activeDashboard.content.layout}`)
  }
  dashboardWidgets.addWidget(widgetId, content, generalSettings, filterContext, layout)
  openWizard.value = false
  isDashboardEditingMode.value = true
}

function editWidget(widgetId: string) {
  widgetToEdit.value = widgetId
  const widgetSpec = dashboardsManager.activeDashboard.value!.model.content.widgets[widgetId]
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
  dashboardWidgets.updateWidget(widgetId, content, generalSettings, filterContext)

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
  const widget = dashboardsManager.activeDashboard.value!.model.content.widgets[widgetId]
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
  // avoid showing the new dashboard, while the dashboard list is loading
  const postCreateMode = nextStep === 'viewList' ? null : 'setDashboardAsActive'
  const key = await dashboardsManager.createDashboard(
    dashboardId,
    settings,
    layout,
    scopeIds,
    postCreateMode
  )
  isDashboardEditingMode.value = false

  if (nextStep === 'setFilters') {
    dashboardFilterSettingsStartingWindow.value = 'filter-configuration'
    openDashboardFilterSettings.value = true
    const updatedDashboardUrl = urlHandler.getDashboardUrl(key, {})
    urlHandler.updateCurrentUrl(updatedDashboardUrl)
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
  const key = dashboardsManager.activeDashboardKey.value
  if (!key) {
    throw new Error('No active dashboard to clone from')
  }
  openDashboardCloneDialog.value = false
  isCloning.value = true
  try {
    let newOwner
    if (layout === DashboardLayout.RELATIVE_GRID) {
      const response = await dashboardAPI.cloneAsRelativeGridDashboard(
        key.name,
        key.owner,
        dashboardId,
        generalSettings
      )
      newOwner = response.extensions.owner
    } else {
      const response = await dashboardAPI.cloneAsResponsiveGridDashboard(
        key.name,
        key.owner,
        dashboardId,
        generalSettings
      )
      newOwner = response.extensions.owner
    }
    if (nextStep === 'setFilters') {
      const newKey: DashboardKey = {
        name: dashboardId,
        owner: newOwner
      }
      await setAsActiveDashboard(newKey, layout)
      await nextTick()
      openDashboardFilterSettings.value = true
    } else if (nextStep === 'viewList') {
      redirectToListDashboardsPage()
    } else {
      throw new Error(`Unknown next step: ${nextStep}`)
    }
  } finally {
    isCloning.value = false
  }
}

const redirectToListDashboardsPage = () => {
  window.location.href = props.links.list_dashboards
}

const handleApplyRuntimeFilters = (filters: ConfiguredFilters, mode: RuntimeFilterMode) => {
  dashboardFilters.handleApplyRuntimeFilters(filters)
  dashboardFilters.setRuntimeFiltersMode(mode)

  const urlSearchParams = dashboardFilters.getRuntimeFiltersSearchParams()
  const updatedDashboardUrl = urlHandler.updateWithPreserve(
    window.location.href,
    ['name'],
    urlSearchParams
  )
  urlHandler.updateCurrentUrl(updatedDashboardUrl)
}

const handleSaveFilterSettings = async (payload: {
  dashboardFilters: ConfiguredFilters
  mandatoryRuntimeFilters: string[]
}) => {
  dashboardFilters.handleSaveDashboardFilters(payload.dashboardFilters)
  dashboardFilters.handleSaveMandatoryRuntimeFilters(payload.mandatoryRuntimeFilters)
  await dashboardsManager.persistDashboard()
}

function closeFilterSettings() {
  openDashboardFilterSettings.value = false
  dashboardFilterSettingsStartingWindow.value = 'runtime-filters'
}

const updateDashboardSettings = async (
  dashboardName: string,
  generalSettings: DashboardGeneralSettings
) => {
  const key = dashboardsManager.activeDashboardKey.value!
  const newKey: DashboardKey = {
    name: dashboardName,
    owner: key.owner
  }
  dashboardsManager.activeDashboard.value!.model.general_settings = generalSettings
  await dashboardsManager.persistDashboard(dashboardName)
  openDashboardSettings.value = false

  const updatedDashboardUrl = urlHandler.getDashboardUrl(
    newKey,
    dashboardFilters.getRuntimeFiltersSearchParams()
  )
  urlHandler.updateCurrentUrl(updatedDashboardUrl)
}

function deepClone<T>(obj: T): T {
  return structuredClone(obj)
}
</script>

<template>
  <CmkErrorBoundary>
    <div>
      <DashboardBreadcrumb
        :selected-dashboard="selectedDashboard ?? null"
        :selected-dashboard-breadcrumb="selectedDashboardBreadcrumb"
        :initial-breadcrumb="initial_breadcrumb"
      />
      <DashboardMenuHeader
        v-model:is-edit-mode="isDashboardEditingMode"
        :selected-dashboard="selectedDashboard"
        :is-dashboard-loading="isDashboardLoading"
        :can-edit-dashboard="dashboardsManager.activeDashboard.value?.metadata.is_editable ?? false"
        :link-user-guide="props.links.user_guide"
        :link-navigation-embedding-page="props.links.navigation_embedding_page"
        :public-token="dashboardsManager.activeDashboard.value?.model.public_token ?? null"
        :is-empty-dashboard="Object.entries(dashboardWidgets.widgetCores.value).length === 0"
        @open-filter="openDashboardFilterSettings = true"
        @open-settings="openDashboardSettings = true"
        @open-clone-workflow="openDashboardCloneDialog = true"
        @open-widget-workflow="openAddWidgetDialog = true"
        @open-share-workflow="openDashboardShareDialog = true"
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
        :logged-in-user="logged_in_user"
        @create-dashboard="(...args) => createDashboard(...args)"
        @cancel-creation="redirectToListDashboardsPage"
      />
      <CloneDashboardWizard
        v-if="dashboardsManager.isInitialized.value"
        v-model:open="openDashboardCloneDialog"
        :active-dashboard-id="dashboardsManager.activeDashboardKey.value?.name ?? ''"
        :available-layouts="available_layouts"
        :reference-dashboard-general-settings="
          deepClone(dashboardsManager.activeDashboard.value!.model.general_settings)
        "
        :reference-dashboard-restricted-to-single="
          deepClone(
            dashboardsManager.activeDashboard.value!.model.filter_context.restricted_to_single || []
          )
        "
        :reference-dashboard-layout-type="
          dashboardsManager.activeDashboard.value!.model.content.layout.type as DashboardLayout
        "
        :reference-dashboard-type="dashboardsManager.activeDashboard.value!.model.type"
        :logged-in-user="logged_in_user"
        @clone-dashboard="(...args) => cloneDashboard(...args)"
        @cancel-clone="openDashboardCloneDialog = false"
      />
      <DashboardSharingWizard
        v-if="openDashboardShareDialog && dashboardsManager.activeDashboardKey.value"
        :dashboard-key="dashboardsManager.activeDashboardKey.value!"
        :public-token="dashboardsManager.activeDashboard?.value?.model.public_token || null"
        :available-features="available_features"
        @refresh-dashboard-settings="dashboardsManager.refreshActiveDashboard"
        @close="openDashboardShareDialog = false"
      />
      <AddWidgetDialog
        v-model:open="openAddWidgetDialog"
        :workflow-items="dashboardWidgetWorkflows"
        :available-features="available_features"
        @select="handleAddWidget"
        @close="openAddWidgetDialog = false"
      />
      <WizardSelector
        :is-open="openWizard"
        :selected-wizard="selectedWizard"
        :dashboard-key="dashboardsManager.activeDashboardKey.value!"
        :context-filters="dashboardFilters.contextFilters.value || {}"
        :dashboard-constants="dashboardsManager.constants.value!"
        :edit-widget-spec="getWidgetSpecToEdit(widgetToEdit ?? null)"
        :edit-widget-id="widgetToEdit"
        :available-features="available_features"
        @back-button="handleWizardSelectorGoBack"
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
        :can-edit="dashboardsManager.activeDashboard.value?.metadata.is_editable ?? false"
        :is-built-in="dashboardsManager.activeDashboard.value?.metadata.is_built_in ?? false"
        :starting-window="dashboardFilterSettingsStartingWindow"
        @apply-runtime-filters="handleApplyRuntimeFilters"
        @save-filter-settings="handleSaveFilterSettings"
        @close="closeFilterSettings"
      />
      <DashboardSettingsWizard
        v-if="openDashboardSettings && dashboardsManager.activeDashboard.value"
        :active-dashboard-id="dashboardsManager.activeDashboardKey.value!.name"
        :dashboard-general-settings="
          deepClone(dashboardsManager.activeDashboard.value!.model.general_settings)
        "
        :dashboard-restricted-to-single="
          dashboardsManager.activeDashboard.value!.model.filter_context.restricted_to_single!
        "
        :logged-in-user="logged_in_user"
        @cancel="openDashboardSettings = false"
        @save="updateDashboardSettings"
      />
    </div>
    <template v-if="dashboardsManager.isInitialized.value">
      <AddWidgetPage
        v-if="Object.entries(dashboardWidgets.widgetCores.value).length === 0"
        :workflow-items="dashboardWidgetWorkflows"
        :available-features="available_features"
        @select="handleAddWidget"
      />
      <DashboardComponent
        v-else-if="dashboardsManager.isInitialized.value"
        :key="`${dashboardsManager.activeDashboardKey.value?.owner}-${dashboardsManager.activeDashboardKey.value?.name}`"
        v-model:dashboard="dashboardsManager.activeDashboard.value!.model"
        :dashboard-key="dashboardsManager.activeDashboardKey.value!"
        :base-filters="dashboardFilters.baseFilters"
        :widget-cores="dashboardWidgets.widgetCores"
        :widget-titles="widgetTitles"
        :constants="dashboardsManager.constants.value!"
        :is-editing="isDashboardEditingMode"
        @widget:edit="editWidget($event)"
        @widget:delete="dashboardWidgets.deleteWidget($event)"
        @widget:clone="(oldWidgetId, newLayout) => cloneWidget(oldWidgetId, newLayout)"
      />
    </template>
    <template v-else>
      <AddWidgetPage
        v-if="openDashboardCreationDialog || openDashboardCloneDialog"
        :workflow-items="dashboardWidgetWorkflows"
        :available-features="available_features"
      />
      <CmkIcon
        v-if="isCloning || !(openDashboardCreationDialog || openDashboardCloneDialog)"
        name="load-graph"
        size="xxlarge"
      />
    </template>
  </CmkErrorBoundary>
</template>
