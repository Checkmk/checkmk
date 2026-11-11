<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onScopeDispose, ref, watch } from 'vue'

import {
  initGlobalTime,
  useGlobalRefresh,
  useGlobalTimePickerRange
} from '@/graphing/GlobalTimePicker'
import { CANVAS_MARGIN_HORIZONTAL } from '@/graphing/components/constants'
import {
  type GraphNoticeDescriptor,
  hasPlottableData,
  useGraphNotice,
  useNoDataNotice
} from '@/graphing/composables/useGraphNotice'
import { useRequestedTimeRange } from '@/graphing/composables/useRequestedTimeRange'
import type { PanelKey, RequestedTimeRange } from '@/graphing/types'
import { type Preview, fetchPreview } from '@/mode-alerts/preview-client'
import {
  type LevelColors,
  hasPredictiveLevels,
  thresholdLines
} from '@/mode-alerts/threshold-lines'
import type { ServiceNameMatch, ThresholdsValue } from '@/mode-alerts/types'
import PreviewGraphFrame from '@/mode-custom-services/PreviewGraphFrame.vue'

const props = defineProps<{
  matchType: ServiceNameMatch
  pattern: string
  thresholds: ThresholdsValue
  timePicker: GlobalTimePickerProps
  levelColors: LevelColors
}>()

const { _t } = usei18n()

const PANEL_KEY: PanelKey = 0
const DEFAULT_FIGURE_WIDTH = 900
const DEBOUNCE_MS = 400

initGlobalTime({
  intervalSeconds: props.timePicker.refresh.interval_seconds,
  start: { type: 'page_default', live: true }
})
const { range: timePickerRange } = useGlobalTimePickerRange(props.timePicker.default_time_range)
const { requestedTimeRange, setRequestedTimeRange, rangeChange } = useRequestedTimeRange()
const { pauseRefresh, refreshTick, contentReloadPending } = useGlobalRefresh()

const figureWidth = ref(DEFAULT_FIGURE_WIDTH)

const preview = ref<Preview | null>(null)
const answeredTimeRange = ref<RequestedTimeRange | undefined>(undefined)
const failedTimeRange = ref<RequestedTimeRange | undefined>(undefined)
const isLoading = ref(false)
const error = ref<string | null>(null)

let requestCounter = 0
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function load(): Promise<void> {
  const requestId = ++requestCounter
  const range = requestedTimeRange.value
  const canvasWidth = Math.max(1, figureWidth.value - CANVAS_MARGIN_HORIZONTAL)
  const step = Math.max(60, Math.ceil((range.end - range.start) / canvasWidth))
  isLoading.value = true
  failedTimeRange.value = undefined
  try {
    const result = await fetchPreview(props.matchType, props.pattern, range, step)
    if (requestId !== requestCounter) {
      return
    }
    preview.value = result
    answeredTimeRange.value = { start: range.start, end: range.end }
    error.value = null
  } catch (e) {
    if (requestId !== requestCounter) {
      return
    }
    error.value = e instanceof Error ? e.message : String(e)
    failedTimeRange.value = { start: range.start, end: range.end }
  } finally {
    if (requestId === requestCounter) {
      isLoading.value = false
    }
  }
}

function refetch(): void {
  if (debounceTimer !== null) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  void load()
}

onScopeDispose(() => {
  if (debounceTimer !== null) {
    clearTimeout(debounceTimer)
  }
})

// The thresholds are not part of the request: editing one only moves its line.
watch(
  () =>
    JSON.stringify({
      matchType: props.matchType,
      pattern: props.pattern,
      requestedTimeRange: requestedTimeRange.value,
      figureWidth: figureWidth.value,
      refreshTick: refreshTick.value
    }),
  () => {
    if (contentReloadPending()) {
      return
    }
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(refetch, DEBOUNCE_MS)
  }
)
void load()

const metrics = computed(() => preview.value?.metrics ?? [])

const horizontalLines = computed(() => {
  const metricLines = preview.value?.horizontal_lines ?? []
  const unit = metrics.value[0]?.metadata.unit
  if (unit === undefined) {
    return metricLines
  }
  return [
    ...metricLines,
    ...thresholdLines(props.thresholds, unit, props.levelColors, {
      upper: { warning: _t('Warning'), critical: _t('Critical') },
      lower: { warning: _t('Warning (lower)'), critical: _t('Critical (lower)') }
    })
  ]
})

const fetchNotice = useGraphNotice({
  error: () => error.value,
  isLoading: () => isLoading.value,
  partialErrors: () => preview.value?.errors ?? [],
  warnings: () => preview.value?.warnings ?? []
})

const noDataNotice = useNoDataNotice()

const previewNotice = computed<GraphNoticeDescriptor | null>(() => {
  const notice = preview.value?.notice
  return notice ? { variant: 'info', message: _t('Nothing to preview'), description: notice } : null
})

const hidesPredictiveLevels = computed(() => hasPredictiveLevels(props.thresholds))

const notice = computed(
  () =>
    fetchNotice.value ??
    previewNotice.value ??
    (isLoading.value || hasPlottableData(metrics.value) ? null : noDataNotice)
)
</script>

<template>
  <div class="mode-alerts-alert-preview-graph">
    <PreviewGraphFrame
      v-model:time-picker-range="timePickerRange"
      v-model:figure-width="figureWidth"
      :time-picker="timePicker"
      :title="pattern"
      :metrics="metrics"
      :data-time-range="preview?.time_range"
      :answered-time-range="answeredTimeRange"
      :failed-time-range="failedTimeRange"
      :horizontal-lines="horizontalLines"
      fit-horizontal-lines
      :requested-time-range="requestedTimeRange"
      :range-change="rangeChange"
      :panel-key="PANEL_KEY"
      :notice="notice"
      @update:requested-time-range="setRequestedTimeRange($event, PANEL_KEY)"
      @inspect="pauseRefresh"
      @retry="refetch"
    />
    <CmkAlert
      v-if="hidesPredictiveLevels"
      variant="warning"
      size="small"
      :text="_t('Predictive thresholds cannot be shown in this graph.')"
    />
  </div>
</template>

<style scoped>
.mode-alerts-alert-preview-graph {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
