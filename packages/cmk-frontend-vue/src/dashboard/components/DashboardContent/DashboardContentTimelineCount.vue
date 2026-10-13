<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkKpiStatCard from '@/dashboard/components/CmkKpiStatCard'
import { useRangedComputedWidget } from '@/dashboard/composables/useComputedWidget'
import type { TimelineContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types.ts'

const VALUE_COLOR = 'var(--font-color)'

const props = defineProps<ContentProps<TimelineContent>>()
const { state, retry } = useRangedComputedWidget(
  props,
  dashboardAPI.computeTimelineCount,
  () => props.content.render_mode.time_range === 'dashboard'
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
