<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { ref } from 'vue'

import { GlobalTimePicker } from '@/graphing/GlobalTimePicker'
import GraphPanel from '@/graphing/components/GraphPanel.vue'
import type { HorizontalLine, Metric, TimeRange } from '@/graphing/components/TimeSeriesGraph'
import {
  clippedToNavigableTime,
  navigableBounds
} from '@/graphing/components/TimeSeriesGraph/interaction/timeBounds'
import type { GraphNoticeDescriptor } from '@/graphing/composables/useGraphNotice'
import type { PanelKey, RangeChange, RequestedTimeRange } from '@/graphing/types'

defineProps<{
  timePicker: GlobalTimePickerProps
  title: string
  metrics: Metric[]
  dataTimeRange: TimeRange | undefined
  horizontalLines: HorizontalLine[]
  requestedTimeRange: RequestedTimeRange
  rangeChange: RangeChange | undefined
  panelKey: PanelKey
  notice: GraphNoticeDescriptor | null
}>()

const emit = defineEmits<{
  'update:requestedTimeRange': [range: RequestedTimeRange]
  inspect: []
  retry: []
}>()

const timePickerRange = defineModel<DateTimeRange>('timePickerRange', { required: true })
const figureWidth = defineModel<number>('figureWidth', { required: true })

const graphContainer = ref<HTMLElement | null>(null)
const { observe } = useResizeObserver((entries) => {
  const width = entries[0]!.contentBoxSize![0]!.inlineSize
  if (width > 0) {
    figureWidth.value = Math.round(width)
  }
})
observe(graphContainer)

function onPanelTimeRange(requested: RequestedTimeRange): void {
  emit('update:requestedTimeRange', clippedToNavigableTime(requested, navigableBounds()))
}
</script>

<template>
  <div ref="graphContainer" class="mode-custom-services-preview-graph-frame">
    <GlobalTimePicker
      v-model="timePickerRange"
      :custom-time-ranges="timePicker.custom_time_ranges"
      :server-time-zone="timePicker.server_time_zone"
      :first-day-of-week="timePicker.first_day_of_week"
    />
    <GraphPanel
      :metrics="metrics"
      :data-time-range="dataTimeRange"
      :horizontal-lines="horizontalLines"
      :requested-time-range="requestedTimeRange"
      :panel-key="panelKey"
      :range-change="rangeChange"
      :title="title"
      show-title
      show-timestamp
      show-legend
      :figure-width="figureWidth"
      :figure-height="200"
      :interaction="{
        brush: 'disabled',
        burger: 'disabled',
        hover: 'enabled',
        panning: 'enabled',
        zoom: 'enabled',
        pin: 'disabled'
      }"
      @update:requested-time-range="onPanelTimeRange"
      @inspect="emit('inspect')"
    >
      <template #notice>
        <CmkSurfaceNotice
          v-if="notice"
          v-bind="notice"
          class="mode-custom-services-preview-graph-frame__notice"
          @retry="emit('retry')"
        />
      </template>
    </GraphPanel>
  </div>
</template>

<style scoped>
.mode-custom-services-preview-graph-frame {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.mode-custom-services-preview-graph-frame__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
}
</style>
