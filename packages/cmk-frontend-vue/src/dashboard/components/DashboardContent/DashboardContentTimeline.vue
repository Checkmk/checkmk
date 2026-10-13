<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { TimelineContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import {
  type BinUnit,
  type FetchedGraph,
  type GraphFetchParams,
  GraphFigure,
  type GraphFigureSource,
  fetchedGraphOf
} from '@/graphing'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<TimelineContent>>()
const { source, headers } = useWidgetSource(props)

const barChart = computed(() => {
  const renderMode = props.content.render_mode
  if (renderMode.type !== 'bar_chart') {
    throw new Error('The timeline bar chart renders the bar chart mode only.')
  }
  return renderMode
})
const binUnit = computed<BinUnit>(() => barChart.value.time_resolution)

async function fetchBars({ fetchWindow }: GraphFetchParams): Promise<FetchedGraph> {
  try {
    const { value } = await dashboardAPI.computeTimeline(
      {
        source: source.value,
        time_range: { start: isoOf(fetchWindow.start), end: isoOf(fetchWindow.end) },
        step: fetchWindow.step
      },
      headers
    )
    return fetchedGraphOf(value)
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode === 404) {
      return {
        title: '',
        metrics: [],
        timeRange: { ...fetchWindow },
        horizontalLines: [],
        shadedRegions: [],
        errors: [],
        warnings: []
      }
    }
    throw error
  }
}

function isoOf(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toISOString()
}

const figureSource = computed<GraphFigureSource>(() => ({
  type: 'fetch',
  key: JSON.stringify([props.content, props.effective_filter_context]),
  fetch: fetchBars,
  binUnit: binUnit.value
}))
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-timeline" :class="{ 'db-content-timeline--preview': isPreview }">
      <CmkSurfaceNotice
        v-if="barChart.time_range === 'dashboard'"
        variant="info"
        :message="_t('This widget follows the dashboard time range')"
        :description="_t('The bar chart does not support the dashboard time range yet.')"
      />
      <GraphFigure
        v-else
        :source="figureSource"
        :timerange="barChart.time_range"
        :show-legend="false"
        :show-pin="false"
        :show-burger-menu="false"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-timeline {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;

  &.db-content-timeline--preview {
    pointer-events: none;
  }
}
</style>
