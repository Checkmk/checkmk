<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import CmkSurfaceNotice from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, ref } from 'vue'

import {
  GlobalTimePicker,
  initGlobalRefresh,
  useGlobalRefresh,
  useGlobalTimePickerRange
} from '@/graphing/GlobalTimePicker'
import GraphPanel from '@/graphing/components/GraphPanel.vue'
import {
  clippedToNavigableTime,
  navigableBounds
} from '@/graphing/components/TimeSeriesGraph/interaction/timeBounds'
import {
  type GraphNoticeDescriptor,
  hasPlottableData,
  useGraphNotice,
  useNoDataNotice
} from '@/graphing/composables/useGraphNotice'
import { useRequestedTimeRange } from '@/graphing/composables/useRequestedTimeRange'
import { useCustomGraphData } from '@/graphing/designer/composables/useCustomGraphData'
import { consolidationFromWire } from '@/graphing/designer/consolidation'
import { DEFAULT_TITLE_MACRO, type GraphItem } from '@/graphing/designer/types'
import type { PanelKey, RequestedTimeRange } from '@/graphing/types'

const props = defineProps<{
  metricName: string | null
  attributeFilter: AttributeFilter | undefined
  consolidation: WireConsolidationFunction
  aggregator: Aggregator | undefined
  timePicker: GlobalTimePickerProps
}>()

const { _t } = usei18n()

const PANEL_KEY: PanelKey = 0
const DEFAULT_FIGURE_WIDTH = 900

initGlobalRefresh({ intervalSeconds: props.timePicker.refresh.interval_seconds, live: true })
const { range: timePickerRange } = useGlobalTimePickerRange(props.timePicker.default_time_range)
const { requestedTimeRange, setRequestedTimeRange, rangeChange } = useRequestedTimeRange()
const { pauseRefresh } = useGlobalRefresh()

const graphContainer = ref<HTMLElement | null>(null)
const figureWidth = ref(DEFAULT_FIGURE_WIDTH)
const { observe } = useResizeObserver((entries) => {
  const width = entries[0]!.contentBoxSize![0]!.inlineSize
  if (width > 0) {
    figureWidth.value = Math.round(width)
  }
})
observe(graphContainer)

const items = computed<GraphItem[]>(() =>
  props.metricName === null
    ? []
    : [
        {
          id: 'A',
          type: 'telemetry_metrics',
          title: DEFAULT_TITLE_MACRO,
          line_type: 'line',
          mirrored: false,
          visible: true,
          metric_name: props.metricName,
          attribute_filter: props.attributeFilter ?? { type: 'and', conjuncts: [] },
          consolidation_function: consolidationFromWire(props.consolidation),
          ...(props.aggregator === undefined ? {} : { aggregator: props.aggregator })
        }
      ]
)

const data = useCustomGraphData({
  getItems: () => items.value,
  getGraphOptions: () => ({
    unit: { type: 'first_entry_with_unit' },
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: false
  }),
  getRequestedTimeRange: () => requestedTimeRange.value,
  getConsolidationFn: () => 'max',
  getFigureWidth: () => figureWidth.value,
  getOverviewRange: () => null
})

function onPanelTimeRange(requested: RequestedTimeRange): void {
  setRequestedTimeRange(clippedToNavigableTime(requested, navigableBounds()), PANEL_KEY)
}

const fetchNotice = useGraphNotice({
  error: () => data.error.value,
  isLoading: () => data.isLoading.value,
  partialErrors: () => data.partialErrors.value,
  warnings: () => data.warnings.value
})

const noDataNotice = useNoDataNotice()

const noMetricNotice = computed<GraphNoticeDescriptor | null>(() =>
  props.metricName === null
    ? {
        variant: 'info',
        message: _t('No metric selected'),
        description: _t('Select a metric to see its graph')
      }
    : null
)

const notice = computed(
  () =>
    fetchNotice.value ??
    noMetricNotice.value ??
    (data.isLoading.value || hasPlottableData(data.metrics.value) ? null : noDataNotice)
)
</script>

<template>
  <div ref="graphContainer" class="mode-custom-services-metric-preview-graph">
    <GlobalTimePicker
      v-model="timePickerRange"
      :custom-time-ranges="timePicker.custom_time_ranges"
      :server-time-zone="timePicker.server_time_zone"
      :first-day-of-week="timePicker.first_day_of_week"
    />
    <GraphPanel
      :metrics="data.metrics.value"
      :data-time-range="data.dataTimeRange.value"
      :horizontal-lines="data.horizontalLines.value"
      :requested-time-range="requestedTimeRange"
      :panel-key="PANEL_KEY"
      :range-change="rangeChange"
      :title="metricName ?? ''"
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
      @inspect="pauseRefresh"
    >
      <template #notice>
        <CmkSurfaceNotice
          v-if="notice"
          v-bind="notice"
          class="mode-custom-services-metric-preview-graph__notice"
          @retry="data.refetch()"
        />
      </template>
    </GraphPanel>
  </div>
</template>

<style scoped>
.mode-custom-services-metric-preview-graph {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.mode-custom-services-metric-preview-graph__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
}
</style>
