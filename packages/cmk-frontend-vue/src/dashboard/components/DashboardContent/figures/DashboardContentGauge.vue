<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkGaugeFigure from '@/dashboard/components/figures/CmkGaugeFigure.vue'
import { useRangedComputedWidget } from '@/dashboard/composables/useComputedWidget'
import type { GaugeContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<GaugeContent>>()
const { state, retry } = useRangedComputedWidget(
  props,
  dashboardAPI.computeGauge,
  () => props.content.time_range !== 'current' && props.content.time_range.window === 'dashboard'
)
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value, width, height }">
      <CmkGaugeFigure
        :value="value"
        :width="width"
        :height="height"
        :filters="effective_filter_context.filters"
      />
    </template>
  </WidgetFigureFrame>
</template>
