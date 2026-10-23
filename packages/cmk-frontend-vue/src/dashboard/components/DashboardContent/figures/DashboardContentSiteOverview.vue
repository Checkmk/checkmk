<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSiteOverviewHostsFigure from '@/dashboard/components/figures/CmkSiteOverviewHostsFigure.vue'
import CmkSiteOverviewSitesFigure from '@/dashboard/components/figures/CmkSiteOverviewSitesFigure.vue'
import { useComputedWidget } from '@/dashboard/composables/useComputedWidget'
import type { SiteOverviewContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'

import type { ContentProps } from '../types'
import WidgetFigureFrame from './WidgetFigureFrame.vue'

const props = defineProps<ContentProps<SiteOverviewContent>>()
const { state, retry } = useComputedWidget(props, dashboardAPI.computeSiteOverview)
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value, width, height }">
      <CmkSiteOverviewHostsFigure
        v-if="value.mode === 'hosts'"
        :value="value"
        :width="width"
        :height="height"
        :hexagon-size="content.hexagon_size"
        :filters="effective_filter_context.filters"
      />
      <CmkSiteOverviewSitesFigure
        v-else
        :value="value"
        :width="width"
        :height="height"
        :hexagon-size="content.hexagon_size"
        :filters="effective_filter_context.filters"
      />
    </template>
  </WidgetFigureFrame>
</template>
