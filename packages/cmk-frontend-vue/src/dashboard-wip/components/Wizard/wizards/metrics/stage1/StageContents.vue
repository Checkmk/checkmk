<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import SingleMultiWidgetObjectFilterConfiguration from '@/dashboard-wip/components/Wizard/components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import type { ElementSelection } from '@/dashboard-wip/components/Wizard/types'
import {
  Graph,
  MetricSelection,
  useSelectGraphTypes
} from '@/dashboard-wip/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard-wip/components/filter/types'
import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import AvailableWidgets from '../../../components/WidgetSelection/AvailableWidgets.vue'
import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import MetricSelector from './MetricSelector/MetricSelector.vue'
import type { UseCombinedMetric } from './MetricSelector/useCombinedMetric'
import type { UseSingleMetric } from './MetricSelector/useSingleMetric'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
}

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: ObjectType): void
  (e: 'goNext'): void
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<Emits>()

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

const hostObjectType = 'host'
const serviceObjectType = 'service'

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const serviceFilterType = defineModel<ElementSelection>('serviceFilterType', { required: true })

const metricType = defineModel<MetricSelection>('metricType', { required: true })

const singleMetricHandler = defineModel<UseSingleMetric>('singleMetricHandler', { required: true })
const combinedMetricHandler = defineModel<UseCombinedMetric>('combinedMetricHandler', {
  required: true
})

const enabledWidgets = useSelectGraphTypes(hostFilterType, serviceFilterType, metricType)
const availableWidgets: WidgetItemList = [
  { id: Graph.SINGLE_GRAPH, label: _t('Single graph'), icon: 'graph' },
  { id: Graph.GAUGE, label: _t('Gauge'), icon: 'gauge' },
  { id: Graph.SINGLE_METRIC, label: _t('Single metric'), icon: 'single-metric' },
  { id: Graph.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
  { id: Graph.SCATTERPLOT, label: _t('Scatterplot'), icon: 'scatterplot' },
  { id: Graph.TOP_LIST, label: _t('Top list'), icon: 'top-list' },
  { id: Graph.PERFORMANCE_GRAPH, label: _t('Performance graph'), icon: 'graph' },
  { id: Graph.COMBINED_GRAPH, label: _t('Combined graph'), icon: 'graph' }
]

// Filters
const filterDefinitions = useFilterDefinitions()
const configuredFiltersByObjectType = computed(() =>
  parseFilters(
    props.widgetConfiguredFilters,
    props.widgetActiveFilters,
    filterDefinitions,
    new Set(['host', 'service'])
  )
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
  <SingleMultiWidgetObjectFilterConfiguration
    v-model:mode-selection="hostFilterType"
    :object-type="hostObjectType"
    :configured-filters-of-object-type="configuredFiltersByObjectType[hostObjectType] || {}"
    :context-filters="contextFilters"
    :in-selection-menu-focus="isInFilterSelectionMenuFocus(hostObjectType)"
    @set-focus="emit('set-focus', $event)"
    @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    @reset-object-type-filters="emit('reset-object-type-filters', $event)"
  />

  <ContentSpacer />

  <CmkHeading type="h2">
    {{ _t('Service selection') }}
  </CmkHeading>
  <SingleMultiWidgetObjectFilterConfiguration
    v-model:mode-selection="serviceFilterType"
    :object-type="serviceObjectType"
    :configured-filters-of-object-type="configuredFiltersByObjectType[serviceObjectType] || {}"
    :context-filters="contextFilters"
    :in-selection-menu-focus="isInFilterSelectionMenuFocus(serviceObjectType)"
    @set-focus="emit('set-focus', $event)"
    @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
    @reset-object-type-filters="emit('reset-object-type-filters', $event)"
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

  <AvailableWidgets :available-items="availableWidgets" :enabled-widgets="enabledWidgets" />

  <ContentSpacer />
</template>
