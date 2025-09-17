<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, h, ref } from 'vue'

import usei18n from '@/lib/i18n'

import { type Filters, useFilters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
// Local components
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import AddFilters from '../../components/AddFilters/AddFilters.vue'
import { useAddFilter } from '../../components/AddFilters/composables/useAddFilters'
import ContentSpacer from '../../components/ContentSpacer.vue'
import FiltersRecap from '../../components/FiltersRecap/FiltersRecap.vue'
import { squashFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import { ElementSelection } from '../../types'
import { MetricSelection } from './composables/useSelectGraphTypes'
import { useCombinedMetric } from './stage1/MetricSelector/useCombinedMetric'
import { useSingleMetric } from './stage1/MetricSelector/useSingleMetric'
import Stage1 from './stage1/StageContents.vue'
import Stage2 from './stage2/StageContents.vue'

const { _t } = usei18n()

interface MetricsWizardProps {
  dashboardName: string
  dashboardFilters?: ConfiguredFilters
  quickFilters?: ConfiguredFilters
  dashboardConstants: DashboardConstants
}

const props = withDefaults(defineProps<MetricsWizardProps>(), {
  dashboardFilters: () => {
    return {} as ConfiguredFilters
  },
  quickFilters: () => {
    return {} as ConfiguredFilters
  }
})

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const addFilters = useAddFilter()

// /////////////////////////////////////////////////////////
// TODO: Fill with saved values if available --v--
// Stage 1
const filters: Filters = useFilters()
const hostFilterType = ref<ElementSelection>(ElementSelection.SPECIFIC)
const serviceFilterType = ref<ElementSelection>(ElementSelection.SPECIFIC)
const metricType = ref<MetricSelection>(MetricSelection.SINGLE_METRIC)
const singleMetricHandler = useSingleMetric(null, null, null)
const combinedMetricHandler = useCombinedMetric(null)

// Stage 2

// TODO: Fill with saved values if available --^--
// /////////////////////////////////////////////////////////

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

const _getConfiguredFilters = (): ConfiguredFilters => {
  const configuredActiveFilters: ConfiguredFilters = {}
  for (const flt of filters.activeFilters.value) {
    configuredActiveFilters[flt] = filters.getFilterValues(flt) || {}
  }
  return configuredActiveFilters
}

const recapAndNext = () => {
  wizardStages[0]!.recapContent = h(FiltersRecap, {
    metricType: metricType.value,
    singleMetric: singleMetricHandler.singleMetric.value,
    combinedMetric: combinedMetricHandler.combinedMetric.value,
    dashboardFilters: props.dashboardFilters,
    quickFilters: props.quickFilters,
    widgetFilters: _getConfiguredFilters()
  })
  addFilters.close()
  wizardHandler.next()
}

const appliedFilters = computed((): ConfiguredFilters => {
  return squashFilters(props.dashboardFilters, props.quickFilters, _getConfiguredFilters())
})

const selectedMetric = computed((): string => {
  return (
    (metricType.value === MetricSelection.SINGLE_METRIC
      ? singleMetricHandler.singleMetric.value
      : combinedMetricHandler.combinedMetric.value) || ''
  )
})
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer v-if="addFilters.isOpen.value">
      <AddFilters :handler="addFilters" :filters="filters" />
    </WizardStepsContainer>

    <WizardStepsContainer v-else>
      <StepsHeader
        :title="_t('Metrics & graphs')"
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
        v-model:metric-type="metricType"
        v-model:single-metric-handler="singleMetricHandler"
        v-model:combined-metric-handler="combinedMetricHandler"
        :dashboard-filters="props.dashboardFilters"
        :quick-filters="props.quickFilters"
        :filters="filters"
        :add-filter-handler="addFilters"
        @go-next="recapAndNext"
      />
      <Suspense>
        <Stage2
          v-if="wizardHandler.stage.value === 1"
          :dashboard-name="dashboardName"
          :dashboard-constants="dashboardConstants"
          :host-filter-type="hostFilterType"
          :service-filter-type="serviceFilterType"
          :metric-type="metricType"
          :filters="appliedFilters"
          :metric="selectedMetric"
          @go-prev="wizardHandler.prev"
          @add-widget="
            (content, generalSettings, filterContext) =>
              emit('addWidget', content, generalSettings, filterContext)
          "
        />
      </Suspense>
    </WizardStageContainer>
  </WizardContainer>
</template>
