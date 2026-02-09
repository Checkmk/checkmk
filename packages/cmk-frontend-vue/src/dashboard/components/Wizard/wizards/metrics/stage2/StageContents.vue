<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import { ElementSelection, type UseWidgetHandler } from '@/dashboard/components/Wizard/types'
import {
  Graph,
  MetricSelection,
  getAvailableGraphs
} from '@/dashboard/components/Wizard/wizards/metrics/composables/useSelectGraphTypes'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import ContentSpacer from '../../../components/ContentSpacer.vue'
import SectionBlock from '../../../components/SectionBlock.vue'
import Stage2Header from '../../../components/Stage2Header.vue'
import SelectableWidgets from '../../../components/WidgetSelection/SelectableWidgets.vue'
import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import { getGraph } from '../utils'
import BarplotWidget from './BarplotWidget/BarplotWidget.vue'
import { type UseBarplot, useBarplot } from './BarplotWidget/composables/useBarplot'
import CombinedGraphWidget from './CombinedGraphWidget/CombinedGraphWidget.vue'
import {
  type UseCombinedGraph,
  useCombinedGraph
} from './CombinedGraphWidget/composables/useCombinedGraph'
import GaugeWidget from './GaugeWidget/GaugeWidget.vue'
import { type UseGauge, useGauge } from './GaugeWidget/composables/useGauge'
import GraphWidget from './GraphWidget/GraphWidget.vue'
import { type UseGraph, useGraph } from './GraphWidget/composables/useGraph'
import MetricWidget from './MetricWidget/MetricWidget.vue'
import { type UseMetric, useMetric } from './MetricWidget/composables/useMetric'
import PerformanceGraphWidget from './PerformanceGraphWidget/PerformanceGraphWidget.vue'
import {
  type UsePerformanceGraph,
  usePerformanceGraph
} from './PerformanceGraphWidget/composables/usePerformanceGraph'
import ScatterplotWidget from './ScatterplotWidget/ScatterplotWidget.vue'
import { type UseScatterplot, useScatterplot } from './ScatterplotWidget/composables/useScatterplot'
import TopListWidget from './TopListWidget/TopListWidget.vue'
import { type UseTopList, useTopList } from './TopListWidget/composables/useTopList'

const { _t } = usei18n()

interface Stage2Props {
  dashboardKey: DashboardKey
  hostFilterType: ElementSelection
  serviceFilterType: ElementSelection
  metricType: MetricSelection

  filters: ConfiguredFilters
  widgetFilters: ConfiguredFilters
  metric: string

  editWidgetSpec: WidgetSpec | null
  preselectedWidgetType?: string | null
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

  const activeHandler = [Graph.COMBINED_GRAPH, Graph.PERFORMANCE_GRAPH].includes(
    selectedWidget.value
  )
    ? handler[Graph.ANY_GRAPH]
    : handler[selectedWidget.value]
  const isValid = activeHandler?.validate()

  if (isValid) {
    const widgetPops = activeHandler!.widgetProps.value
    emit('addWidget', toValue(widgetPops.content), toValue(widgetPops.general_settings), {
      uses_infos: toValue(widgetPops.effective_filter_context.uses_infos),
      filters: props.widgetFilters
    } as WidgetFilterContext)
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
  { id: Graph.SINGLE_GRAPH, label: _t('Graph'), icon: 'graph' },
  { id: Graph.SINGLE_METRIC, label: _t('Metric'), icon: 'single-metric' },
  { id: Graph.GAUGE, label: _t('Gauge'), icon: 'gauge' }
]

const availableWidgetsBottom: WidgetItemList = [
  { id: Graph.BARPLOT, label: _t('Barplot'), icon: 'barplot' },
  { id: Graph.SCATTERPLOT, label: _t('Scatterplot'), icon: 'scatterplot' },
  { id: Graph.TOP_LIST, label: _t('Top list'), icon: 'top-list' }
]

const selectedWidget = ref<Graph | null>(
  getGraph(enabledWidgets, props.preselectedWidgetType || props.editWidgetSpec?.content?.type)
)

let handler: Partial<Record<Graph, UseWidgetHandler>> = {}

if (props.metricType === MetricSelection.SINGLE_METRIC) {
  handler = {
    [Graph.SINGLE_GRAPH]: await useGraph(props.metric, props.filters, props.editWidgetSpec),

    [Graph.SINGLE_METRIC]: await useMetric(props.metric, props.filters, props.editWidgetSpec),

    [Graph.GAUGE]: await useGauge(props.metric, props.filters, props.editWidgetSpec),

    [Graph.BARPLOT]: await useBarplot(props.metric, props.filters, props.editWidgetSpec),

    [Graph.SCATTERPLOT]: await useScatterplot(props.metric, props.filters, props.editWidgetSpec),

    [Graph.TOP_LIST]: await useTopList(props.metric, props.filters, props.editWidgetSpec)
  }

  selectedWidget.value =
    selectedWidget.value === Graph.ANY_GRAPH ? Graph.SINGLE_GRAPH : selectedWidget.value
} else {
  const isPerformanceGraph: boolean =
    props.hostFilterType === ElementSelection.SPECIFIC &&
    props.serviceFilterType === ElementSelection.SPECIFIC
  const graphHandler = isPerformanceGraph ? usePerformanceGraph : useCombinedGraph
  selectedWidget.value = isPerformanceGraph ? Graph.PERFORMANCE_GRAPH : Graph.COMBINED_GRAPH

  handler = {
    [Graph.ANY_GRAPH]: await graphHandler(props.metric, props.filters, props.editWidgetSpec)
  }
}
</script>

<template>
  <Stage2Header :edit="!!editWidgetSpec" @back="gotoPrevStage" @save="gotoNextStage" />

  <div v-if="metricType === MetricSelection.SINGLE_METRIC">
    <SectionBlock :title="_t('Choose how to display your data')">
      <SelectableWidgets
        v-model:selected-widget="selectedWidget as Graph"
        :available-items="availableWidgetsTop"
        :enabled-widgets="enabledWidgets"
      />

      <ContentSpacer :dimension="6" />

      <SelectableWidgets
        v-model:selected-widget="selectedWidget as Graph"
        :available-items="availableWidgetsBottom"
        :enabled-widgets="enabledWidgets"
      />
    </SectionBlock>
  </div>
  <div v-if="metricType === MetricSelection.SINGLE_METRIC">
    <GaugeWidget
      v-if="selectedWidget === Graph.GAUGE"
      v-model:handler="handler[Graph.GAUGE] as unknown as UseGauge"
      :dashboard-key="dashboardKey"
    />
    <GraphWidget
      v-if="selectedWidget === Graph.SINGLE_GRAPH"
      v-model:handler="handler[Graph.SINGLE_GRAPH] as unknown as UseGraph"
      :dashboard-key="dashboardKey"
    />
    <MetricWidget
      v-if="selectedWidget === Graph.SINGLE_METRIC"
      v-model:handler="handler[Graph.SINGLE_METRIC] as unknown as UseMetric"
      :dashboard-key="dashboardKey"
    />

    <BarplotWidget
      v-if="selectedWidget === Graph.BARPLOT"
      v-model:handler="handler[Graph.BARPLOT] as unknown as UseBarplot"
      :dashboard-key="dashboardKey"
    />

    <ScatterplotWidget
      v-if="selectedWidget === Graph.SCATTERPLOT"
      v-model:handler="handler[Graph.SCATTERPLOT] as unknown as UseScatterplot"
      :dashboard-key="dashboardKey"
    />

    <TopListWidget
      v-if="selectedWidget === Graph.TOP_LIST"
      v-model:handler="handler[Graph.TOP_LIST] as unknown as UseTopList"
      :dashboard-key="dashboardKey"
    />
  </div>
  <div v-else>
    <PerformanceGraphWidget
      v-if="selectedWidget === Graph.PERFORMANCE_GRAPH"
      v-model:handler="handler[Graph.ANY_GRAPH] as unknown as UsePerformanceGraph"
      :dashboard-key="dashboardKey"
    />

    <CombinedGraphWidget
      v-if="selectedWidget === Graph.COMBINED_GRAPH"
      v-model:handler="handler[Graph.ANY_GRAPH] as unknown as UseCombinedGraph"
      :dashboard-key="dashboardKey"
    />
  </div>
</template>
