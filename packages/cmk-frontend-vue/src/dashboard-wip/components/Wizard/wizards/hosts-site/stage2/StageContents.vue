<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'

import ActionBar from '../../../components/ActionBar.vue'
import ActionButton from '../../../components/ActionButton.vue'
import ContentSpacer from '../../../components/ContentSpacer.vue'
import type { ElementSelection, UseWidgetHandler } from '../../../types'
import WidgetSelection from '../components/WidgetSelection.vue'
import { getAvailableGraphs } from '../composables/useSelectGraphTypes'
import { Graph } from '../types'
import HostState from './HostState/HostState.vue'
import { type UseHostState, useHostState } from './HostState/composables/useHostState'
import HostStateSummary from './HostStateSummary/HostStateSummary.vue'
import {
  type UseHostStateSummary,
  useHostStateSummary
} from './HostStateSummary/composables/useHostStateSummary'
import HostStatistics from './HostStatistics/HostStatistics.vue'
import {
  type UseHostStatistics,
  useHostStatistics
} from './HostStatistics/composables/useHostStatistics'
import SiteOverview from './SiteOverview/SiteOverview.vue'
import { type UseSiteOverview, useSiteOverview } from './SiteOverview/composables/useSiteOverview'

const { _t } = usei18n()

interface Stage2Props {
  dashboardName: string
  hostFilterType: ElementSelection

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

const availableGraphs = getAvailableGraphs(props.hostFilterType)
const selectedWidget = ref<Graph>(Graph.SITE_OVERVIEW)

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.HOST_STATE]: await useHostState(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.HOST_STATE_SUMMARY]: await useHostStateSummary(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.HOST_STATISTICS]: await useHostStatistics(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  ),
  [Graph.SITE_OVERVIEW]: await useSiteOverview(
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
    <ActionButton :label="_t('Add & place widget')" :action="gotoNextStage" variant="secondary" />
  </ActionBar>

  <ContentSpacer />

  <WidgetSelection
    v-model:selected-widget="selectedWidget as Graph"
    :available-items="Object.keys(Graph)"
    :enabled-widgets="availableGraphs"
  />

  <ContentSpacer />

  <HostState
    v-if="selectedWidget === Graph.HOST_STATE"
    v-model:handler="handler[Graph.HOST_STATE] as unknown as UseHostState"
    :dashboard-name="dashboardName"
  />

  <HostStateSummary
    v-if="selectedWidget === Graph.HOST_STATE_SUMMARY"
    v-model:handler="handler[Graph.HOST_STATE_SUMMARY] as unknown as UseHostStateSummary"
    :dashboard-name="dashboardName"
  />

  <HostStatistics
    v-if="selectedWidget === Graph.HOST_STATISTICS"
    v-model:handler="handler[Graph.HOST_STATISTICS] as unknown as UseHostStatistics"
    :dashboard-name="dashboardName"
  />

  <SiteOverview
    v-if="selectedWidget === Graph.SITE_OVERVIEW"
    v-model:handler="handler[Graph.SITE_OVERVIEW] as unknown as UseSiteOverview"
    :dashboard-name="dashboardName"
  />
</template>
