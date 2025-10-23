<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, h, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { randomId } from '@/lib/randomId'

import type { ContentProps } from '@/dashboard-wip/components/DashboardContent/types'
import AddFilters from '@/dashboard-wip/components/Wizard/components/AddFilters/AddFilters.vue'
import {
  parseContextConfiguredFilters,
  squashFilters
} from '@/dashboard-wip/components/Wizard/components/FiltersRecap/utils.ts'
import { useWidgetVisualizationProps } from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import { useWidgetFilterManager } from '@/dashboard-wip/components/Wizard/components/filter/composables/useWidgetFilterManager.ts'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type {
  EffectiveWidgetFilterContext,
  EmbeddedViewContent,
  LinkedViewContent,
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import CloseButton from '../../components/CloseButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'
import Stage3 from './stage3/StageContents.vue'
import type { CopyExistingViewSelection, NewViewSelection, ViewSelection } from './types'
import { DataConfigurationMode } from './types'

const { _t } = usei18n()

interface ViewWizardProps {
  dashboardName: string
  dashboardOwner: string
  dashboardConstants: DashboardConstants
  contextFilters: ContextFilters
  editWidget?: ContentProps | null
}

const props = withDefaults(defineProps<ViewWizardProps>(), {
  editWidget: null
})

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

function getDefaultWidgetId(): string {
  if (props.editWidget) {
    return props.editWidget.widget_id
  }
  return randomId()
}

function getDefaultDatasource(): string | null {
  if (props.editWidget && props.editWidget.content.type === 'embedded_view') {
    return props.editWidget.content.datasource
  }
  return null
}

function getDefaultRestrictedToSingle(): string[] {
  if (props.editWidget && props.editWidget.content.type === 'embedded_view') {
    return props.editWidget.content.restricted_to_single
  }
  return []
}

function getDefaultReferencedViewName(): string | null {
  if (props.editWidget && props.editWidget.content.type === 'linked_view') {
    return props.editWidget.content.view_name
  }
  return null
}

function getConfigMode(mode: DataConfigurationMode): DataConfigurationMode {
  if (props.editWidget) {
    return DataConfigurationMode.EDIT
  }
  return mode
}

function getDefaultContent(): EmbeddedViewContent | LinkedViewContent | undefined {
  if (props.editWidget) {
    return props.editWidget.content as EmbeddedViewContent | LinkedViewContent
  }
  return undefined
}

const widgetId = ref<string>(getDefaultWidgetId())

// Stage 1
const filterDefinitions = useFilterDefinitions()
const initialFilters = props.editWidget ? props.editWidget.effective_filter_context.filters : {}
const widgetFilterManager = useWidgetFilterManager(initialFilters, filterDefinitions)

const selectedDatasource = ref<string | null>(getDefaultDatasource())
const contextInfos = ref<string[]>([])
const restrictedToSingleInfos = ref<string[]>(getDefaultRestrictedToSingle())
const originalViewName = ref<string | null>(null)
const referencedViewName = ref<string | null>(getDefaultReferencedViewName())

// Stage 2
const dataConfigurationMode = ref<DataConfigurationMode>(
  getConfigMode(DataConfigurationMode.CREATE)
)
const embeddedId = ref<string>()
const viewSelection = ref<NewViewSelection | CopyExistingViewSelection>()

// Stage 3
const content = ref<EmbeddedViewContent | LinkedViewContent | undefined>(getDefaultContent())
const visualizationProps = useWidgetVisualizationProps('')

const wizardHandler = useWizard(3)
const wizardStages: QuickSetupStageSpec[] = [
  {
    title: _t('Data selection'),
    actions: [],
    errors: []
  },
  {
    title: _t('Data configuration'),
    actions: [],
    errors: []
  },
  {
    title: _t('Visualization'),
    actions: [],
    errors: []
  }
]

function stage1GoNext(selectedView: ViewSelection) {
  widgetFilterManager.closeSelectionMenu() // ensure filter menu is closed
  // TODO: this and stage 1 needs to handle edit mode
  if (selectedView.type === 'link') {
    wizardStages[0]!.recapContent = h(
      'div',
      _t('Link to view: %{viewName}', { viewName: selectedView.viewName })
    )
    content.value = {
      type: 'linked_view',
      view_name: selectedView.viewName
    } as LinkedViewContent
    // skip data config stage
    wizardHandler.goto(2)
  } else {
    if (selectedView.type === 'new') {
      wizardStages[0]!.recapContent = h(
        'div',
        _t('New view based on: %{datasource}', { datasource: selectedView.datasource })
      )
    } else if (selectedView.type === 'copy') {
      wizardStages[0]!.recapContent = h(
        'div',
        _t('Copy existing view: %{viewName}', { viewName: selectedView.viewName })
      )
    }
    dataConfigurationMode.value = DataConfigurationMode.CREATE
    embeddedId.value = randomId()
    viewSelection.value = selectedView as NewViewSelection | CopyExistingViewSelection
    wizardHandler.next()
  }
}

function stage2GoNext(embeddedViewContent: EmbeddedViewContent) {
  content.value = embeddedViewContent
  wizardHandler.next()
}

function stage3GoPrev() {
  if (content.value?.type === 'linked_view') {
    // stage 2 doesn't exist for linked views, so go back to stage 1
    wizardHandler.goto(0)
  } else {
    // the user already saved an embedded view in stage 2
    // we need to change the mode to EDIT, so the editor page can load the existing data
    dataConfigurationMode.value = DataConfigurationMode.EDIT
    wizardHandler.prev()
  }
}

function stage3SaveWidget(generalSettings: WidgetGeneralSettings) {
  if (!content.value) {
    throw new Error('No content defined')
  }
  emit('addWidget', content.value, generalSettings, {
    uses_infos: contextInfos.value,
    filters: widgetFilterManager.getConfiguredFilters()
  } as WidgetFilterContext)
}

const effectiveFilterContext = computed<EffectiveWidgetFilterContext>(() => {
  return {
    uses_infos: contextInfos.value,
    filters: squashFilters(
      parseContextConfiguredFilters(props.contextFilters),
      widgetFilterManager.getConfiguredFilters()
    ),
    restricted_to_single:
      props.dashboardConstants.widgets['embedded_view']!.filter_context.restricted_to_single
  } as EffectiveWidgetFilterContext
})

const currentFilterSelectionFocus = computed(() => {
  if (!widgetFilterManager.selectionMenuOpen.value) {
    return null
  }
  return widgetFilterManager.selectionMenuCurrentTarget.value
})

const handleObjectTypeSwitch = (objectType: string): void => {
  widgetFilterManager.closeSelectionMenu()
  widgetFilterManager.resetFilterValuesOfObjectType(objectType)
}

const handleResetAllFilters = (): void => {
  widgetFilterManager.closeSelectionMenu()
  widgetFilterManager.resetFilterValuesOfObjectType()
}
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer v-if="widgetFilterManager.selectionMenuOpen.value">
      <AddFilters
        :filter-selection-target="widgetFilterManager.selectionMenuCurrentTarget.value"
        :close="widgetFilterManager.closeSelectionMenu"
        :filters="widgetFilterManager.filterHandler"
      />
    </WizardStepsContainer>
    <WizardStepsContainer v-else>
      <StepsHeader
        :title="_t('View')"
        :subtitle="_t('Define widget')"
        @back="() => emit('goBack')"
      />

      <ContentSpacer />

      <QuickSetup
        :loading="false"
        :current-stage="wizardHandler.stage.value"
        :regular-stages="wizardStages"
        :mode="wizardHandler.mode"
        :prevent-leaving="false"
        :hide-wait-icon="true"
      />
    </WizardStepsContainer>

    <WizardStageContainer>
      <CloseButton @close="() => emit('goBack')" />
      <Stage1
        v-if="wizardHandler.stage.value === 0"
        v-model:selected-datasource="selectedDatasource"
        v-model:context-infos="contextInfos"
        v-model:restricted-to-single-infos="restrictedToSingleInfos"
        v-model:original-view-name="originalViewName"
        v-model:referenced-view-name="referencedViewName"
        :widget-configured-filters="widgetFilterManager.getConfiguredFilters()"
        :widget-active-filters="widgetFilterManager.getSelectedFilters()"
        :context-filters="contextFilters"
        :current-filter-selection-menu-focus="currentFilterSelectionFocus"
        @go-next="stage1GoNext"
        @set-focus="widgetFilterManager.openSelectionMenu"
        @update-filter-values="
          (filterId, values) => widgetFilterManager.updateFilterValues(filterId, values)
        "
        @reset-all-filters="handleResetAllFilters"
        @reset-object-type-filters="handleObjectTypeSwitch"
      />
      <Stage2
        v-if="wizardHandler.stage.value === 1"
        :dashboard-name="dashboardName"
        :dashboard-owner="dashboardOwner"
        :embedded-id="embeddedId!"
        :configuration-mode="dataConfigurationMode"
        :view-selection="viewSelection!"
        @go-prev="wizardHandler.prev"
        @go-next="stage2GoNext"
      />
      <Stage3
        v-if="wizardHandler.stage.value === 2"
        v-model:visualization="visualizationProps"
        :dashboard-name="dashboardName"
        :widget_id="widgetId"
        :content="content!"
        :effective_filter_context="effectiveFilterContext"
        @go-prev="stage3GoPrev"
        @add-widget="stage3SaveWidget"
      />
    </WizardStageContainer>
  </WizardContainer>
</template>
