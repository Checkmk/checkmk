<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBarplotFigure from '@/dashboard/components/figures/CmkBarplotFigure.vue'
import { useComputedWidget } from '@/dashboard/composables/useComputedWidget'
import type { BarplotContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<BarplotContent>>()
const { state, retry } = useComputedWidget(props, dashboardAPI.computeBarplot)
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value, width, height }">
      <CmkBarplotFigure
        :value="value"
        :width="width"
        :height="height"
        :filters="effective_filter_context.filters"
      />
    </template>
  </WidgetFigureFrame>
</template>
