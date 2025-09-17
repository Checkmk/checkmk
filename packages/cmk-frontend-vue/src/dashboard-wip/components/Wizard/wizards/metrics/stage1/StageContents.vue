<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { inject } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import HostFilter from '@/dashboard-wip/components/Wizard/components/HostServiceSelector/HostFilter.vue'
import ServiceFilter from '@/dashboard-wip/components/Wizard/components/HostServiceSelector/ServiceFilter.vue'
import type { ElementSelection } from '@/dashboard-wip/components/Wizard/types'
import AvailableGraphs from '@/dashboard-wip/components/Wizard/wizards/metrics/components/AvailableGraphs.vue'
import {
  MetricSelection,
  useSelectGraphTypes
} from '@/dashboard-wip/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'
import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard-wip/components/filter/types'

import type { UseAddFilter } from '../../../components/AddFilters/composables/useAddFilters'
import { useFiltersLogic } from '../../../components/HostServiceSelector/composables/useFiltersLogic'
import MetricSelector from './MetricSelector/MetricSelector.vue'
import type { UseCombinedMetric } from './MetricSelector/useCombinedMetric'
import type { UseSingleMetric } from './MetricSelector/useSingleMetric'

const { _t } = usei18n()

interface Stage1Props {
  dashboardFilters: ConfiguredFilters
  quickFilters: ConfiguredFilters
  filters: Filters
  addFilterHandler: UseAddFilter
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<{
  goNext: []
}>()

const gotoNextStage = () => {
  /*
  TODOs:
  - Filter validation
  - Return processed data
  */

  const handler =
    metricType.value === MetricSelection.SINGLE_METRIC
      ? singleMetricHandler.value
      : combinedMetricHandler.value

  const isValid = handler.validate()
  if (isValid) {
    emit('goNext')
  }
}

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const serviceFilterType = defineModel<ElementSelection>('serviceFilterType', { required: true })
const metricType = defineModel<MetricSelection>('metricType', { required: true })

const singleMetricHandler = defineModel<UseSingleMetric>('singleMetricHandler', { required: true })
const combinedMetricHandler = defineModel<UseCombinedMetric>('combinedMetricHandler', {
  required: true
})

const availableGraphs = useSelectGraphTypes(hostFilterType, serviceFilterType, metricType)

// Filters
const filterDefinitions = inject('filterDefinitions') as Record<string, FilterDefinition>
const serviceFilterLogic = useFiltersLogic(
  props.filters,
  filterDefinitions,
  serviceFilterType,
  'service',
  'service'
)
const hostFilterLogic = useFiltersLogic(
  props.filters,
  filterDefinitions,
  hostFilterType,
  'host',
  'host',
  (value: string) => ({ host: value, neg_host: '' })
)
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Widget data') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Next step: Visualization')"
      :icon="{ name: 'continue', side: 'right' }"
      :action="gotoNextStage"
      variant="secondary"
    />
  </ActionBar>

  <ContentSpacer />

  <CmkParagraph>
    {{ _t('Select the data you want to analyze') }} <br />
    {{ _t("Dashboard filters apply here and don't have to be selected again") }}
  </CmkParagraph>

  <ContentSpacer />

  <CmkHeading type="h2">
    {{ _t('Host selection') }}
  </CmkHeading>
  <HostFilter
    v-model:host-selection="hostFilterType"
    v-model:host-filter-logic="hostFilterLogic"
    :dashboard-filters="dashboardFilters"
    :quick-filters="quickFilters"
    :widget-filters="filters"
    :add-filter-handler="addFilterHandler"
  />

  <ContentSpacer />

  <CmkHeading type="h2">
    {{ _t('Service selection') }}
  </CmkHeading>
  <ServiceFilter
    v-model:service-selection="serviceFilterType"
    v-model:service-filter-logic="serviceFilterLogic"
    :dashboard-filters="dashboardFilters"
    :quick-filters="quickFilters"
    :widget-filters="filters"
    :add-filter-handler="addFilterHandler"
  />

  <ContentSpacer />

  <CmkHeading type="h2">
    {{ _t('Metric selection') }}
  </CmkHeading>

  <MetricSelector
    v-model:metric-type="metricType"
    v-model:single-metric-handler="singleMetricHandler"
    v-model:combined-metric-handler="combinedMetricHandler"
  />

  <ContentSpacer />

  <CmkHeading type="h3">
    {{ _t('Available visualization types') }}
  </CmkHeading>

  <AvailableGraphs :available-graphs="availableGraphs" />

  <ContentSpacer />
</template>
