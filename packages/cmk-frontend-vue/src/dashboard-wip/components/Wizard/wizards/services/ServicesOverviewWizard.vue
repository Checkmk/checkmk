<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, h, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import { useWidgetFilterManager } from '@/dashboard-wip/components/Wizard/components/filter/composables/useWidgetFilterManager.ts'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
// Local components
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import AddFilters from '../../components/AddFilters/AddFilters.vue'
import { useAddFilter } from '../../components/AddFilters/composables/useAddFilters'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FiltersRecap from '../../components/FiltersRecap/FiltersRecap.vue'
import { parseContextConfiguredFilters, squashFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import { ElementSelection } from '../../types'
import { getConfiguredFilters } from '../../utils'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'

const { _t } = usei18n()

interface ServicesOverviewWizardProps {
  dashboardName: string
  contextFilters: ContextFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec?: WidgetSpec | null
}

const props = defineProps<ServicesOverviewWizardProps>()

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

const filterDefinitions = useFilterDefinitions()

const widgetFilterManager = useWidgetFilterManager({}, filterDefinitions)

const addFilters = useAddFilter()

const hostFilterType = ref<ElementSelection>(ElementSelection.SPECIFIC)
const serviceFilterType = ref<ElementSelection>(ElementSelection.SPECIFIC)

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

const recapAndNext = () => {
  widgetFilterManager.closeSelectionMenu()
  wizardStages[0]!.recapContent = h(FiltersRecap, {
    metricType: null,
    singleMetric: null,
    combinedMetric: null,
    contextConfiguredFilters: contextConfiguredFilters.value,
    widgetFilters: getConfiguredFilters(widgetFilterManager)
  })
  addFilters.close()
  wizardHandler.next()
}

const appliedFilters = computed((): ConfiguredFilters => {
  return squashFilters(contextConfiguredFilters.value, getConfiguredFilters(widgetFilterManager))
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
        :title="_t('ServicesOverview & graphs')"
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
      />
      <Suspense>
        <Stage2
          v-if="wizardHandler.stage.value === 1"
          :dashboard-name="dashboardName"
          :dashboard-constants="dashboardConstants"
          :host-filter-type="hostFilterType"
          :service-filter-type="serviceFilterType"
          :filters="appliedFilters"
          :edit-widget-spec="editWidgetSpec ?? null"
          @go-prev="wizardHandler.prev"
          @add-widget="
            (content, generalSettings, filterContext) =>
              emit('addWidget', content, generalSettings, filterContext)
          "
          @update-widget="
            (content, generalSettings, filterContext) =>
              emit('updateWidget', content, generalSettings, filterContext)
          "
        />
        <template #fallback>
          <CmkIcon name="load-graph" size="xxlarge" />
        </template>
      </Suspense>
    </WizardStageContainer>
  </WizardContainer>
</template>
