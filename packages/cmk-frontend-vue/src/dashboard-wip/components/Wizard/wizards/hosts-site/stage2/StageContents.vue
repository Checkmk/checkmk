<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, toValue } from 'vue'

import usei18n from '@/lib/i18n'

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
import type { ElementSelection, UseWidgetHandler } from '../../../types'
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
  widgetFilters: ConfiguredFilters
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

const gotoNextStage = () => {
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

const enabledWidgets = getAvailableGraphs(props.hostFilterType, props.availableFeatures)
const availableWidgets: WidgetItemList = [
  { id: Graph.SITE_OVERVIEW, label: _t('Site overview'), icon: 'site-overview' },
  { id: Graph.HOST_STATISTICS, label: _t('Host statistics'), icon: 'folder' },
  { id: Graph.HOST_STATE, label: _t('Host state'), icon: 'folder' },
  { id: Graph.HOST_STATE_SUMMARY, label: _t('Host state summary'), icon: 'folder' }
]

function getSelectedWidget(): Graph {
  switch (props.editWidgetSpec?.content?.type) {
    case 'site_overview':
      return Graph.SITE_OVERVIEW
    case 'host_stats':
      return Graph.HOST_STATISTICS
    case 'host_state':
      return Graph.HOST_STATE
    case 'host_state_summary':
      return Graph.HOST_STATE_SUMMARY
  }
  return enabledWidgets[0]!
}
const selectedWidget = ref<Graph>(getSelectedWidget())

const handler: Partial<Record<Graph, UseWidgetHandler>> = {
  [Graph.HOST_STATISTICS]: await useHostStatistics(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )
}

if (props.availableFeatures === DashboardFeatures.UNRESTRICTED) {
  handler[Graph.HOST_STATE] = await useHostState(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )

  handler[Graph.HOST_STATE_SUMMARY] = await useHostStateSummary(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )

  handler[Graph.SITE_OVERVIEW] = await useSiteOverview(
    props.filters,
    props.dashboardConstants,
    props.editWidgetSpec
  )
}

const isUnrestricted = props.availableFeatures === DashboardFeatures.UNRESTRICTED
</script>

<template>
  <Stage2Header :edit="!!editWidgetSpec" @back="gotoPrevStage" @save="gotoNextStage" />

  <SectionBlock :title="_t('Choose how to display your data')">
    <SelectableWidgets
      v-model:selected-widget="selectedWidget as Graph"
      :available-items="availableWidgets"
      :enabled-widgets="enabledWidgets"
    />
  </SectionBlock>

  <HostState
    v-if="selectedWidget === Graph.HOST_STATE && isUnrestricted"
    v-model:handler="handler[Graph.HOST_STATE] as unknown as UseHostState"
    :dashboard-name="dashboardName"
  />

  <HostStateSummary
    v-if="selectedWidget === Graph.HOST_STATE_SUMMARY && isUnrestricted"
    v-model:handler="handler[Graph.HOST_STATE_SUMMARY] as unknown as UseHostStateSummary"
    :dashboard-name="dashboardName"
  />

  <HostStatistics
    v-if="selectedWidget === Graph.HOST_STATISTICS"
    v-model:handler="handler[Graph.HOST_STATISTICS] as unknown as UseHostStatistics"
    :dashboard-name="dashboardName"
  />

  <SiteOverview
    v-if="selectedWidget === Graph.SITE_OVERVIEW && isUnrestricted"
    v-model:handler="handler[Graph.SITE_OVERVIEW] as unknown as UseSiteOverview"
    :dashboard-name="dashboardName"
  />
</template>
