<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import ActionBar from '@/dashboard-wip/components/Wizard/components/ActionBar.vue'
import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import ContentSpacer from '@/dashboard-wip/components/Wizard/components/ContentSpacer.vue'
import type { ElementSelection, UseWidgetHandler } from '@/dashboard-wip/components/Wizard/types'
import {
  Graph,
  MetricSelection,
  getAvailableGraphs
} from '@/dashboard-wip/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'

import SelectableWidgets from '../../../components/WidgetSelection/SelectableWidgets.vue'
import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import BarplotWidget from './BarplotWidget/BarplotWidget.vue'
import { type UseBarplot, useBarplot } from './BarplotWidget/composables/useBarplot'
import GaugeWidget from './GaugeWidget/GaugeWidget.vue'
import { type UseGauge, useGauge } from './GaugeWidget/composables/useGauge'
import GraphWidget from './GraphWidget/GraphWidget.vue'
import { type UseGraph, useGraph } from './GraphWidget/composables/useGraph'
import MetricWidget from './MetricWidget/MetricWidget.vue'
import { type UseMetric, useMetric } from './MetricWidget/composables/useMetric'
import ScatterplotWidget from './ScatterplotWidget/ScatterplotWidget.vue'
import { type UseScatterplot, useScatterplot } from './ScatterplotWidget/composables/useScatterplot'
import TopListWidget from './TopListWidget/TopListWidget.vue'
import { type UseTopList, useTopList } from './TopListWidget/composables/useTopList'

const { _t } = usei18n()

interface Stage2Props {
  dashboardName: string
  hostFilterType: ElementSelection
  serviceFilterType: ElementSelection
  metricType: MetricSelection

  filters: ConfiguredFilters
  metric: string
  dashboardConstants: DashboardConstants
}

const props = defineProps<Stage2Props>()
const emit = defineEmits<{
  goPrev: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const gotoNextStage = () => {
  if (!selectedWidget.value) {
    return
  }

  const activeHandler = handler[selectedWidget.value]
  const isValid = activeHandler?.validate()

  if (isValid) {
    const widgetPops = activeHandler!.widgetProps.value
    emit(
      'addWidget',
      toValue(widgetPops.content),
      toValue(widgetPops.general_settings),
      toValue(widgetPops.effective_filter_context)
    )
  }
}

const gotoPrevStage = () => {
  emit('goPrev')
}

const enabledWidgets = getAvailableGraphs(
  props.hostFilterType,
  props.serviceFilterType,
  props.metricType
)

const availableWidgetsTop: WidgetItemList = [
  { id: Graph.SINGLE_GRAPH, label: _t('Single graph'), icon: 'graph' },
  { id: Graph.SINGLE_METRIC, label: _t('Single metric'), icon: 'single-metric' },
  { id: Graph.GAUGE, label: _t('Gauge'), icon: 'gauge' }
]

const availableWidgetsBottom: WidgetItemList = [
  { id: Graph.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
  { id: Graph.SCATTERPLOT, label: _t('Scatterplot'), icon: 'scatterplot' },
  { id: Graph.TOP_LIST, label: _t('Top list'), icon: 'top-list' }
]

const availableGraphWidgets: WidgetItemList = [
  { id: Graph.PERFORMANCE_GRAPH, label: _t('Performance graph'), icon: 'graph' },
  { id: Graph.COMBINED_GRAPH, label: _t('Combined graph'), icon: 'graph' }
]

const selectedWidget = ref<Graph | null>(enabledWidgets[0] || null)

// TODO: We need to provide the current widget config to the handlers in order to edit it
const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.SINGLE_GRAPH]: useGraph(props.metric, props.filters),
  [Graph.SINGLE_METRIC]: useMetric(props.metric, props.filters),
  [Graph.GAUGE]: useGauge(props.metric, props.filters),
  [Graph.BARPLOT]: useBarplot(props.metric, props.filters),
  [Graph.SCATTERPLOT]: useScatterplot(props.metric, props.filters),
  [Graph.TOP_LIST]: useTopList(props.metric, props.filters)
}
</script>

<template>
  <CmkHeading type="h1">
    {{ _t('Widget data') }}
  </CmkHeading>

  <ContentSpacer />

  <ActionBar align-items="left">
    <ActionButton
      :label="_t('Previous step')"
      :icon="{ name: 'back', side: 'left' }"
      :action="gotoPrevStage"
      variant="secondary"
    />
    <ActionButton :label="_t('Add & place widget')" :action="gotoNextStage" variant="primary" />
  </ActionBar>

  <ContentSpacer />

  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>

  <div v-if="metricType === MetricSelection.SINGLE_METRIC">
    <SelectableWidgets
      v-model:selected-widget="selectedWidget as Graph"
      :available-items="availableWidgetsTop"
      :enabled-widgets="enabledWidgets"
    />

    <ContentSpacer />

    <SelectableWidgets
      v-model:selected-widget="selectedWidget as Graph"
      :available-items="availableWidgetsBottom"
      :enabled-widgets="enabledWidgets"
    />
  </div>
  <div v-else>
    <SelectableWidgets
      v-model:selected-widget="selectedWidget as Graph"
      :available-items="availableGraphWidgets"
      :enabled-widgets="enabledWidgets"
    />
  </div>

  <ContentSpacer />

  <GaugeWidget
    v-if="selectedWidget === Graph.GAUGE"
    v-model:handler="handler[Graph.GAUGE] as unknown as UseGauge"
    :dashboard-name="dashboardName"
  />
  <GraphWidget
    v-if="selectedWidget === Graph.SINGLE_GRAPH"
    v-model:handler="handler[Graph.SINGLE_GRAPH] as unknown as UseGraph"
    :dashboard-name="dashboardName"
  />
  <MetricWidget
    v-if="selectedWidget === Graph.SINGLE_METRIC"
    v-model:handler="handler[Graph.SINGLE_METRIC] as unknown as UseMetric"
    :dashboard-name="dashboardName"
  />

  <BarplotWidget
    v-if="selectedWidget === Graph.BARPLOT"
    v-model:handler="handler[Graph.BARPLOT] as unknown as UseBarplot"
    :dashboard-name="dashboardName"
  />

  <ScatterplotWidget
    v-if="selectedWidget === Graph.SCATTERPLOT"
    v-model:handler="handler[Graph.SCATTERPLOT] as unknown as UseScatterplot"
    :dashboard-name="dashboardName"
  />

  <TopListWidget
    v-if="selectedWidget === Graph.TOP_LIST"
    v-model:handler="handler[Graph.TOP_LIST] as unknown as UseTopList"
    :dashboard-name="dashboardName"
  />
</template>
