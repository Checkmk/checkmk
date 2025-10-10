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
import { Graph, getAvailableGraphs, getAvailableWidgets } from '../composables/useSelectGraphTypes'
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

const enabledWidgets = getAvailableGraphs()
const availableWidgets = getAvailableWidgets()

const selectedWidget = ref<Graph>(Graph.ALERT_OVERVIEW)

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.ALERT_OVERVIEW]: await useAlertOverview(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.ALERT_TIMELINE]: await useAlertTimeline(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.NOTIFICATION_TIMELINE]: await useNotificationTimeline(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.PERCENTAGE_OF_SERVICE_PROBLEMS]: await usePercentageOfServiceProblems(
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
      v-if="!!editWidgetSpec"
      :label="_t('Add & place widget')"
      :action="addWidget"
      variant="secondary"
    />
    <ActionButton v-else :label="_t('Update widget')" :action="addWidget" variant="secondary" />
  </ActionBar>

  <ContentSpacer />

  <SelectableWidgets
    v-model:selected-widget="selectedWidget as Graph"
    :available-items="availableWidgets"
    :enabled-widgets="enabledWidgets"
  />

  <ContentSpacer />

  <AlertOverview
    v-if="selectedWidget === Graph.ALERT_OVERVIEW"
    v-model:handler="handler[Graph.ALERT_OVERVIEW] as unknown as UseAlertOverview"
    :dashboard-name="dashboardName"
  />

  <AlertTimeline
    v-if="selectedWidget === Graph.ALERT_TIMELINE"
    v-model:handler="handler[Graph.ALERT_TIMELINE] as unknown as UseAlertTimeline"
    :dashboard-name="dashboardName"
  />

  <NotificationTimeline
    v-if="selectedWidget === Graph.NOTIFICATION_TIMELINE"
    v-model:handler="handler[Graph.NOTIFICATION_TIMELINE] as unknown as UseNotificationTimeline"
    :dashboard-name="dashboardName"
  />

  <PercentageOfServiceProblems
    v-if="selectedWidget === Graph.PERCENTAGE_OF_SERVICE_PROBLEMS"
    v-model:handler="
      handler[Graph.PERCENTAGE_OF_SERVICE_PROBLEMS] as unknown as UsePercentageOfServiceProblems
    "
    :dashboard-name="dashboardName"
  />
</template>
