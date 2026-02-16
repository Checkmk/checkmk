<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import type { ElementSelection, UseWidgetHandler } from '@/dashboard/components/Wizard/types'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import SectionBlock from '../../../components/SectionBlock.vue'
import Stage2Header from '../../../components/Stage2Header.vue'
import SelectableWidgets from '../../../components/WidgetSelection/SelectableWidgets.vue'
import {
  Graph,
  getAvailableGraphs,
  getAvailableWidgets,
  getGraphFromWidgetType,
  getLogCompatibleGraphs
} from '../composables/useSelectGraphTypes'
import AlertOverview from './AlertOverview/AlertOverview.vue'
import {
  type UseAlertOverview,
  useAlertOverview
} from './AlertOverview/composables/useAlertOverview.ts'
import AlertTimeline from './AlertTimeline/AlertTimeline.vue'
import {
  type UseAlertTimeline,
  useAlertTimeline
} from './AlertTimeline/composables/useAlertTimeline.ts'
import NotificationTimeline from './NotificationTimeline/NotificationTimeline.vue'
import {
  type UseNotificationTimeline,
  useNotificationTimeline
} from './NotificationTimeline/composables/useNotificationTimeline.ts'
import PercentageOfServiceProblems from './PercentageOfServiceProblems/PercentageOfServiceProblems.vue'
import {
  type UsePercentageOfServiceProblems,
  usePercentageOfServiceProblems
} from './PercentageOfServiceProblems/composables/usePercentageOfServiceProblems.ts'

const { _t } = usei18n()

interface Stage2Props {
  dashboardKey: DashboardKey
  hostFilterType: ElementSelection
  serviceFilterType: ElementSelection
  filters: ConfiguredFilters
  widgetFilters: ConfiguredFilters
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

const filterDefinitions = useFilterDefinitions()

const hasLogFilters = computed(() => {
  return Object.keys(props.widgetFilters).some(
    (flt) => filterDefinitions?.[flt]?.extensions?.info === 'log'
  )
})

const enabledWidgets = computed(() =>
  hasLogFilters.value ? getLogCompatibleGraphs() : getAvailableGraphs()
)
const availableWidgets = getAvailableWidgets()

const selectedWidget = ref<Graph>(
  getGraphFromWidgetType(props.preselectedWidgetType || props.editWidgetSpec?.content.type || '')
)

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.ALERT_OVERVIEW]: await useAlertOverview(props.filters, props.editWidgetSpec),
  [Graph.ALERT_TIMELINE]: await useAlertTimeline(props.filters, props.editWidgetSpec),
  [Graph.NOTIFICATION_TIMELINE]: await useNotificationTimeline(props.filters, props.editWidgetSpec),
  [Graph.PROBLEM_GRAPH]: await usePercentageOfServiceProblems(props.filters, props.editWidgetSpec)
}
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

  <AlertOverview
    v-if="selectedWidget === Graph.ALERT_OVERVIEW"
    v-model:handler="handler[Graph.ALERT_OVERVIEW] as unknown as UseAlertOverview"
    :dashboard-key="dashboardKey"
  />

  <AlertTimeline
    v-if="selectedWidget === Graph.ALERT_TIMELINE"
    v-model:handler="handler[Graph.ALERT_TIMELINE] as unknown as UseAlertTimeline"
    :dashboard-key="dashboardKey"
  />

  <NotificationTimeline
    v-if="selectedWidget === Graph.NOTIFICATION_TIMELINE"
    v-model:handler="handler[Graph.NOTIFICATION_TIMELINE] as unknown as UseNotificationTimeline"
    :dashboard-key="dashboardKey"
  />

  <PercentageOfServiceProblems
    v-if="selectedWidget === Graph.PROBLEM_GRAPH"
    v-model:handler="handler[Graph.PROBLEM_GRAPH] as unknown as UsePercentageOfServiceProblems"
    :dashboard-key="dashboardKey"
  />
</template>
