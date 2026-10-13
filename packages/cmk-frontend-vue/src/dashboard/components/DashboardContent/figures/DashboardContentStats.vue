<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStatsFigure from '@/dashboard/components/figures/CmkStatsFigure.vue'
import { useComputedWidget } from '@/dashboard/composables/useComputedWidget'
import type { StatsContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<StatsContent>>()
const { state, retry } = useComputedWidget(props, dashboardAPI.computeStats)
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
      />
    </template>
  </WidgetFigureFrame>
</template>
