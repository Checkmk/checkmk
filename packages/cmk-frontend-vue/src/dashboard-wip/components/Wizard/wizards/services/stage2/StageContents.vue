<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import type { ElementSelection, UseWidgetHandler } from '@/dashboard-wip/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { type DashboardConstants, DashboardFeatures } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

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
  dashboardName: string
  hostFilterType: ElementSelection
  serviceFilterType: ElementSelection
  filters: ConfiguredFilters
  dashboardConstants: DashboardConstants
  editWidgetSpec: WidgetSpec | null
  availableFeatures: DashboardFeatures
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
  props.availableFeatures
)
const availableWidgets: WidgetItemList = [
  { id: Graph.SERVICE_STATE, label: _t('Service state'), icon: 'graph' },
  { id: Graph.SERVICE_STATE_SUMMARY, label: _t('Service state summary'), icon: 'gauge' },
  { id: Graph.SERVICE_STATISTICS, label: _t('Service statistics'), icon: 'single-metric' }
]

function getDefaultSelectedWidget(): Graph | null {
  if (props.editWidgetSpec) {
    switch (props.editWidgetSpec.content.type) {
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
        if (enabledWidgets.includes(Graph.SERVICE_STATISTICS)) {
          return Graph.SERVICE_STATISTICS
        }
        break
    }
  }
  return enabledWidgets[0] ?? null
}
const selectedWidget = ref<Graph | null>(getDefaultSelectedWidget())

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.SERVICE_STATISTICS]: await useServiceStatistics(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )
}

if (props.availableFeatures === DashboardFeatures.UNRESTRICTED) {
  handler[Graph.SERVICE_STATE] = await useServiceState(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )
  handler[Graph.SERVICE_STATE_SUMMARY] = await useServiceStateSummary(
    props.filters,
    props.dashboardConstants,
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
    :dashboard-name="dashboardName"
  />

  <ServiceStateSummary
    v-if="selectedWidget === Graph.SERVICE_STATE_SUMMARY && isUnrestricted"
    v-model:handler="handler[Graph.SERVICE_STATE_SUMMARY] as unknown as UseServiceStateSummary"
    :dashboard-name="dashboardName"
  />

  <ServiceStatistics
    v-if="selectedWidget === Graph.SERVICE_STATISTICS"
    v-model:handler="handler[Graph.SERVICE_STATISTICS] as unknown as UseServiceStatistics"
    :dashboard-name="dashboardName"
  />
</template>
