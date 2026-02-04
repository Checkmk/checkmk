<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, h, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import { useWidgetFilterManager } from '@/dashboard/components/Wizard/components/filter/composables/useWidgetFilterManager.ts'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import { useInjectVisualInfos } from '@/dashboard/composables/useProvideVisualInfos'
// Local components
import type { DashboardConstants, DashboardKey } from '@/dashboard/types/dashboard'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import AddFilters from '../../components/AddFilters/AddFilters.vue'
import { useAddFilter } from '../../components/AddFilters/composables/useAddFilters'
import CloseButton from '../../components/CloseButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FiltersRecap from '../../components/FiltersRecap/FiltersRecap.vue'
import { parseContextConfiguredFilters, squashFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import { ElementSelection } from '../../types'
import { extractConfiguredFilters, getInitialElementSelection } from '../../utils'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'

const { _t } = usei18n()

interface AlertNotificationWizardProps {
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec?: WidgetSpec | null
}

const props = defineProps<AlertNotificationWizardProps>()

const emit = defineEmits<{
  goBack: []
  close: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const filterDefinitions = useFilterDefinitions()

const widgetFilterManager = useWidgetFilterManager(
  props.editWidgetSpec?.filter_context.filters || {},
  filterDefinitions
)

const addFilters = useAddFilter()

const visualInfos = useInjectVisualInfos()
const hostFilterType = ref<ElementSelection>(
  getInitialElementSelection(
    props.dashboardConstants,
    filterDefinitions,
    visualInfos,
    null,
    props.editWidgetSpec,
    'host',
    props.editWidgetSpec ? ElementSelection.MULTIPLE : ElementSelection.SPECIFIC
  )
)
const serviceFilterType = ref<ElementSelection>(
  getInitialElementSelection(
    props.dashboardConstants,
    filterDefinitions,
    visualInfos,
    null,
    props.editWidgetSpec,
    'service',
    props.editWidgetSpec ? ElementSelection.MULTIPLE : ElementSelection.SPECIFIC
  )
)

const wizardHandler = useWizard(2)
const wizardStages: QuickSetupStageSpec[] = [
  {
    title: _t('Data selection'),
    actions: [],
    errors: []
  },
  {
    title: _t('Visualization'),
    actions: [],
    errors: []
  }
]

const contextConfiguredFilters = computed((): ConfiguredFilters => {
  return parseContextConfiguredFilters(props.contextFilters)
})

const preselectedWidgetType: Ref<string | null> = ref(null)
const recapAndNext = (selectedWidgetType: string | null) => {
  preselectedWidgetType.value = selectedWidgetType
  widgetFilterManager.closeSelectionMenu()
  wizardStages[0]!.recapContent = h(FiltersRecap, {
    contextConfiguredFilters: contextConfiguredFilters.value,
    widgetFilters: extractConfiguredFilters(widgetFilterManager)
  })
  addFilters.close()
  wizardHandler.next()
}

const appliedFilters = computed((): ConfiguredFilters => {
  return squashFilters(
    contextConfiguredFilters.value,
    extractConfiguredFilters(widgetFilterManager)
  )
})

const handleObjectTypeSwitch = (objectType: string): void => {
  widgetFilterManager.closeSelectionMenu()
  widgetFilterManager.resetFilterValuesOfObjectType(objectType)
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
        :title="_t('Alert & Notification')"
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
      <CloseButton @close="() => emit('close')" />

      <Stage1
        v-if="wizardHandler.stage.value === 0"
        v-model:host-filter-type="hostFilterType"
        v-model:service-filter-type="serviceFilterType"
        :widget-configured-filters="widgetFilterManager.getConfiguredFilters()"
        :widget-active-filters="widgetFilterManager.getSelectedFilters()"
        :context-filters="contextFilters"
        :is-in-filter-selection-menu-focus="widgetFilterManager.objectTypeIsInFocus"
        @go-next="recapAndNext"
        @set-focus="widgetFilterManager.openSelectionMenu"
        @update-filter-values="
          (filterId, values) => widgetFilterManager.updateFilterValues(filterId, values)
        "
        @reset-object-type-filters="handleObjectTypeSwitch"
        @remove-filter="(filterId) => widgetFilterManager.filterHandler.removeFilter(filterId)"
      />
      <Suspense>
        <Stage2
          v-if="wizardHandler.stage.value === 1"
          :dashboard-key="dashboardKey"
          :dashboard-constants="dashboardConstants"
          :host-filter-type="hostFilterType"
          :service-filter-type="serviceFilterType"
          :filters="appliedFilters"
          :widget-filters="extractConfiguredFilters(widgetFilterManager)"
          :edit-widget-spec="editWidgetSpec ?? null"
          :preselected-widget-type="preselectedWidgetType"
          @go-prev="wizardHandler.prev"
          @add-widget="
            (content, generalSettings, filterContext) =>
              emit('addWidget', content, generalSettings, filterContext)
          "
        />
        <template #fallback>
          <CmkIcon name="load-graph" size="xxlarge" />
        </template>
      </Suspense>
    </WizardStageContainer>
  </WizardContainer>
</template>
