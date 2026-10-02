<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkAlertOverviewFigure from '@/dashboard/components/figures/CmkAlertOverviewFigure.vue'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import { widgetTimeRange } from '@/dashboard/lib/widgetTimeRange'
import type { AlertOverviewContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<AlertOverviewContent>>()
const { source, headers } = useWidgetSource(props)
const timeRange = computed(() => widgetTimeRange(props.range))
const followsDashboardRange = computed(() => props.content.time_range === 'dashboard')
const { state, retry } = useWidgetData(
  () =>
    dashboardAPI.computeAlertOverview(
      { source: source.value, time_range: timeRange.value },
      headers
    ),
  () => [
    props.content,
    props.effective_filter_context,
    followsDashboardRange.value ? timeRange.value : null
  ],
  () => props.tick
)
const interactive = !useInjectIsPublicDashboard()
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value, width, height }">
      <CmkAlertOverviewFigure
        :value="value"
        :width="width"
        :height="height"
        :filters="effective_filter_context.filters"
        :interactive="interactive"
      />
    </template>
  </WidgetFigureFrame>
</template>
