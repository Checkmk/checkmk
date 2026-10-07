<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import { widgetTimeRange } from '@/dashboard/lib/widgetTimeRange'
import type { TimelineContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types.ts'

const VALUE_COLOR = 'var(--font-color)'

const props = defineProps<ContentProps<TimelineContent>>()
const { source, headers } = useWidgetSource(props)
const timeRange = computed(() => widgetTimeRange(props.range))
const followsDashboardRange = computed(() => props.content.render_mode.time_range === 'dashboard')
const { state, retry } = useWidgetData(
  () =>
    dashboardAPI.computeTimelineCount(
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
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value }">
      <CmkKpiStatCard :title="effectiveTitle" :value="String(value.count)" :color="VALUE_COLOR" />
    </template>
  </WidgetFigureFrame>
</template>
