<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import type { ElementSelection, UseWidgetHandler } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { DashboardFeatures, type DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage2Header from '../../../components/Stage2Header.vue'
import SelectableWidgets from '../../../components/WidgetSelection/SelectableWidgets.vue'
import type { WidgetItemList } from '../../../components/WidgetSelection/types'
import { Graph, getAvailableGraphs } from '../composables/useSelectGraphTypes'
import ServiceState from './ServiceState/ServiceState.vue'
import { type UseServiceState, useServiceState } from './ServiceState/composables/useServiceState'
import ServiceStateSummary from './ServiceStateSummary/ServiceStateSummary.vue'
import {
  type UseServiceStateSummary,
  useServiceStateSummary
} from './ServiceStateSummary/composables/useServiceStateSummary'
import ServiceStatistics from './ServiceStatistics/ServiceStatistics.vue'
import {
  type UseServiceStatistics,
  useServiceStatistics
} from './ServiceStatistics/composables/useServiceStatistics'

const { _t } = usei18n()

interface Stage2Props {
  dashboardKey: DashboardKey
  hostFilterType: ElementSelection
  serviceFilterType: ElementSelection
  filters: ConfiguredFilters
  widgetFilters: ConfiguredFilters
  editWidgetSpec: WidgetSpec | null
  availableFeatures: DashboardFeatures
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

const addWidget = () => {
  if (!selectedWidget.value) {
    return
  }

  const activeHandler = handler[selectedWidget.value]
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
  props.availableFeatures
)
const availableWidgets: WidgetItemList = [
  { id: Graph.SERVICE_STATE, label: _t('Service state'), icon: 'graph' },
  { id: Graph.SERVICE_STATE_SUMMARY, label: _t('Service state summary'), icon: 'gauge' },
  { id: Graph.SERVICE_STATS, label: _t('Service statistics'), icon: 'single-metric' }
]

function getDefaultSelectedWidget(): Graph | null {
  const widgetType = props.preselectedWidgetType || props.editWidgetSpec?.content?.type
  if (widgetType) {
    switch (widgetType) {
      case 'service_state':
        if (enabledWidgets.includes(Graph.SERVICE_STATE)) {
          return Graph.SERVICE_STATE
        }
        break
      case 'service_state_summary':
        if (enabledWidgets.includes(Graph.SERVICE_STATE_SUMMARY)) {
          return Graph.SERVICE_STATE_SUMMARY
        }
        break
      case 'service_stats':
        if (enabledWidgets.includes(Graph.SERVICE_STATS)) {
          return Graph.SERVICE_STATS
        }
        break
    }
  }
  return enabledWidgets[0] ?? null
}
const selectedWidget = ref<Graph | null>(getDefaultSelectedWidget())

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.SERVICE_STATS]: await useServiceStatistics(props.filters, props.editWidgetSpec)
}

if (props.availableFeatures === DashboardFeatures.UNRESTRICTED) {
  handler[Graph.SERVICE_STATE] = await useServiceState(props.filters, props.editWidgetSpec)
  handler[Graph.SERVICE_STATE_SUMMARY] = await useServiceStateSummary(
    props.filters,
    props.editWidgetSpec
  )
}

const isUnrestricted = props.availableFeatures === DashboardFeatures.UNRESTRICTED
</script>

<template>
  <Stage2Header :edit="!!editWidgetSpec" @back="gotoPrevStage" @save="addWidget" />

  <SectionBlock :title="_t('Choose how to display your data')">
    <SelectableWidgets
      v-model:selected-widget="selectedWidget as Graph"
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
    />
  </SectionBlock>

  <ServiceState
    v-if="selectedWidget === Graph.SERVICE_STATE && isUnrestricted"
    v-model:handler="handler[Graph.SERVICE_STATE] as unknown as UseServiceState"
    :dashboard-key="dashboardKey"
  />

  <ServiceStateSummary
    v-if="selectedWidget === Graph.SERVICE_STATE_SUMMARY && isUnrestricted"
    v-model:handler="handler[Graph.SERVICE_STATE_SUMMARY] as unknown as UseServiceStateSummary"
    :dashboard-key="dashboardKey"
  />

  <ServiceStatistics
    v-if="selectedWidget === Graph.SERVICE_STATS"
    v-model:handler="handler[Graph.SERVICE_STATS] as unknown as UseServiceStatistics"
    :dashboard-key="dashboardKey"
  />
</template>
