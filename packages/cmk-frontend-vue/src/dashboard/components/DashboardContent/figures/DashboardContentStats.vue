<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStatsFigure from '@/dashboard/components/figures/CmkStatsFigure.vue'
import { useComputedWidget } from '@/dashboard/composables/useComputedWidget'
import { useInjectDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import { statsLinkUrl } from '@/dashboard/lib/contextualLinkUrl'
import type { StatsContent, StatsLinkPart } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'
import { useTimeRangeVariables } from '@/graphing/GlobalTimePicker/timeRangeUrl'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<StatsContent>>()
const { state, retry } = useComputedWidget(props, dashboardAPI.computeStats)
const drillDownSource = useInjectDrillDownSource()
const timeRange = useTimeRangeVariables()

function deferredLinkUrl(part: StatsLinkPart, linkIndex: number): string {
  return statsLinkUrl(
    props.dashboardKey,
    props.widget_id,
    part,
    linkIndex,
    props.effective_filter_context.filters,
    timeRange.value,
    drillDownSource.value
  )
}
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value, width, height }">
      <CmkStatsFigure
        :value="value"
        :width="width"
        :height="height"
        :filters="effective_filter_context.filters"
        :deferred-link-url="deferredLinkUrl"
      />
    </template>
  </WidgetFigureFrame>
</template>
