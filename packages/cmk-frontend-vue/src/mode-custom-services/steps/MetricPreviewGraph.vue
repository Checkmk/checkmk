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
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import {
  initGlobalRefresh,
  useGlobalRefresh,
  useGlobalTimePickerRange
} from '@/graphing/GlobalTimePicker'
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
import type { PanelKey } from '@/graphing/types'
import PreviewGraphFrame from '@/mode-custom-services/PreviewGraphFrame.vue'

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

const figureWidth = ref(DEFAULT_FIGURE_WIDTH)

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
  <PreviewGraphFrame
    v-model:time-picker-range="timePickerRange"
    v-model:figure-width="figureWidth"
    :time-picker="timePicker"
    :title="metricName ?? ''"
    :metrics="data.metrics.value"
    :data-time-range="data.dataTimeRange.value"
    :answered-time-range="data.answeredTimeRange.value"
    :failed-time-range="data.failedTimeRange.value"
    :horizontal-lines="data.horizontalLines.value"
    :requested-time-range="requestedTimeRange"
    :range-change="rangeChange"
    :panel-key="PANEL_KEY"
    :notice="notice"
    @update:requested-time-range="setRequestedTimeRange($event, PANEL_KEY)"
    @inspect="pauseRefresh"
    @retry="data.refetch()"
  />
</template>
