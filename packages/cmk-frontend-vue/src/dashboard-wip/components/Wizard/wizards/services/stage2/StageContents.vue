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
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

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
}

const props = defineProps<Stage2Props>()
const emit = defineEmits<{
  goPrev: []
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

const updateWidget = () => {
  if (!selectedWidget.value) {
    return
  }

  const activeHandler = handler[selectedWidget.value]
  const isValid = activeHandler?.validate()

  if (isValid) {
    const widgetPops = activeHandler!.widgetProps.value
    emit(
      'updateWidget',
      toValue(widgetPops.content),
      toValue(widgetPops.general_settings),
      toValue(widgetPops.effective_filter_context)
    )
  }
}

const gotoPrevStage = () => {
  emit('goPrev')
}

const enabledWidgets = getAvailableGraphs(props.hostFilterType, props.serviceFilterType)
const availableWidgets: WidgetItemList = [
  { id: Graph.SERVICE_STATE, label: _t('Service state'), icon: 'graph' },
  { id: Graph.SERVICE_STATE_SUMMARY, label: _t('Service state summary'), icon: 'gauge' },
  { id: Graph.SERVICE_STATISTICS, label: _t('Service statistics'), icon: 'single-metric' }
]

const selectedWidget = ref<Graph | null>(enabledWidgets[0] ?? null)

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.SERVICE_STATE]: await useServiceState(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.SERVICE_STATE_SUMMARY]: await useServiceStateSummary(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.SERVICE_STATISTICS]: await useServiceStatistics(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )
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
    <ActionButton
      v-if="!editWidgetSpec"
      :label="_t('Add & place widget')"
      :action="addWidget"
      variant="primary"
    />
    <ActionButton v-else :label="_t('Update widget')" :action="updateWidget" variant="secondary" />
  </ActionBar>

  <ContentSpacer />

  <CmkHeading type="h3">{{ _t('Choose how to display your data') }}</CmkHeading>
  <SelectableWidgets
    v-model:selected-widget="selectedWidget as Graph"
    :available-items="availableWidgets"
    :enabled-widgets="enabledWidgets"
  />

  <ContentSpacer />

  <ServiceState
    v-if="selectedWidget === Graph.SERVICE_STATE"
    v-model:handler="handler[Graph.SERVICE_STATE] as unknown as UseServiceState"
    :dashboard-name="dashboardName"
  />

  <ServiceStateSummary
    v-if="selectedWidget === Graph.SERVICE_STATE_SUMMARY"
    v-model:handler="handler[Graph.SERVICE_STATE_SUMMARY] as unknown as UseServiceStateSummary"
    :dashboard-name="dashboardName"
  />

  <ServiceStatistics
    v-if="selectedWidget === Graph.SERVICE_STATISTICS"
    v-model:handler="handler[Graph.SERVICE_STATISTICS] as unknown as UseServiceStatistics"
    :dashboard-name="dashboardName"
  />
</template>
