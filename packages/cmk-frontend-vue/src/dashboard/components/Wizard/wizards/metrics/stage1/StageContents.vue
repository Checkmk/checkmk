<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import SingleMultiWidgetObjectFilterConfiguration from '@/dashboard/components/Wizard/components/filter/SingleMultiWidgetObjectFilterConfiguration.vue'
import { parseFilters } from '@/dashboard/components/Wizard/components/filter/utils.ts'
import { ElementSelection } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils.ts'
import { DashboardFeatures } from '@/dashboard/types/dashboard'
import type { ContextFilters } from '@/dashboard/types/filter.ts'
import type { ObjectType } from '@/dashboard/types/shared.ts'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage1Header from '../../../components/Stage1Header.vue'
import AvailableWidgets from '../../../components/WidgetSelection/AvailableWidgets.vue'
import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import { Graph, MetricSelection, useSelectGraphTypes } from '../composables/useSelectGraphTypes'
import MetricSelector from './MetricSelector/MetricSelector.vue'
import type { UseMetric } from './MetricSelector/useMetric'

const { _t } = usei18n()

interface Stage1Props {
  widgetConfiguredFilters: ConfiguredFilters
  widgetActiveFilters: string[]
  contextFilters: ContextFilters
  isInFilterSelectionMenuFocus: (objectType: ObjectType) => boolean
  availableFeatures: DashboardFeatures
}

interface Emits {
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
  (e: 'reset-object-type-filters', objectType: ObjectType): void
  (e: 'remove-filter', filterId: string): void
  (e: 'goNext', preselectedWidgetType: string | null): void
}

const props = defineProps<Stage1Props>()
const emit = defineEmits<Emits>()

const gotoNextStage = (preselectedWidgetType: string | null = null) => {
  /*
  TODOs:
  - Filter validation
  - Return processed data
  */

  const isValid = metricHandler.value.validate()
  if (isValid) {
    emit('goNext', preselectedWidgetType)
  }
}

const hostObjectType = 'host'
const serviceObjectType = 'service'

const hostFilterType = defineModel<ElementSelection>('hostFilterType', { required: true })
const serviceFilterType = defineModel<ElementSelection>('serviceFilterType', { required: true })

const metricType = defineModel<MetricSelection>('metricType', { required: true })
const metricHandler = defineModel<UseMetric>('metricHandler', { required: true })

const enabledWidgets = useSelectGraphTypes(hostFilterType, serviceFilterType, metricType)
const availableWidgets: WidgetItemList = [
  { id: Graph.ANY_GRAPH, label: _t('Graph'), icon: 'graph' },
  { id: Graph.GAUGE, label: _t('Gauge'), icon: 'gauge' },
  { id: Graph.SINGLE_METRIC, label: _t('Single'), icon: 'single-metric' },
  { id: Graph.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
  { id: Graph.SCATTERPLOT, label: _t('Scatterplot'), icon: 'scatterplot' },
  { id: Graph.TOP_LIST, label: _t('Top list'), icon: 'top-list' }
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

const availableFilterTypes = computed(() =>
  props.availableFeatures === DashboardFeatures.RESTRICTED
    ? [ElementSelection.SPECIFIC]
    : [ElementSelection.SPECIFIC, ElementSelection.MULTIPLE]
)

const availableMetricTypes = computed(() =>
  props.availableFeatures === DashboardFeatures.RESTRICTED
    ? [MetricSelection.COMBINED_GRAPH]
    : [MetricSelection.SINGLE_METRIC, MetricSelection.COMBINED_GRAPH]
)

if (!availableFilterTypes.value.includes(hostFilterType.value)) {
  hostFilterType.value = availableFilterTypes.value[0]!
}

if (!availableFilterTypes.value.includes(serviceFilterType.value)) {
  serviceFilterType.value = availableFilterTypes.value[0]!
}

if (!availableMetricTypes.value.includes(metricType.value)) {
  metricType.value = availableMetricTypes.value[0]!
}
</script>

<template>
  <Stage1Header @click="gotoNextStage" />

  <SectionBlock :title="_t('Host selection')">
    <SingleMultiWidgetObjectFilterConfiguration
      v-model:mode-selection="hostFilterType"
      :object-type="hostObjectType"
      :configured-filters-of-object-type="configuredFiltersByObjectType[hostObjectType] || {}"
      :context-filters="contextFilters"
      :in-selection-menu-focus="isInFilterSelectionMenuFocus(hostObjectType)"
      :available-filter-types="availableFilterTypes"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @reset-object-type-filters="emit('reset-object-type-filters', $event)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>

  <SectionBlock :title="_t('Service selection')">
    <SingleMultiWidgetObjectFilterConfiguration
      v-model:mode-selection="serviceFilterType"
      :object-type="serviceObjectType"
      :configured-filters-of-object-type="configuredFiltersByObjectType[serviceObjectType] || {}"
      :context-filters="contextFilters"
      :in-selection-menu-focus="isInFilterSelectionMenuFocus(serviceObjectType)"
      :available-filter-types="availableFilterTypes"
      @set-focus="emit('set-focus', $event)"
      @update-filter-values="(filterId, values) => emit('update-filter-values', filterId, values)"
      @reset-object-type-filters="emit('reset-object-type-filters', $event)"
      @remove-filter="(filterId) => emit('remove-filter', filterId)"
    />
  </SectionBlock>

  <SectionBlock :title="_t('Metric selection')">
    <MetricSelector
      v-model:metric-type="metricType"
      v-model:metric-handler="metricHandler"
      :available-metric-types="availableMetricTypes"
      :host-selection-mode="hostFilterType"
      :service-selection-mode="serviceFilterType"
    />
  </SectionBlock>

  <SectionBlock :title="_t('Available visualization type')">
    <AvailableWidgets
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
      @select-widget="(preselectedWidgetType) => gotoNextStage(preselectedWidgetType)"
    />
  </SectionBlock>
</template>
