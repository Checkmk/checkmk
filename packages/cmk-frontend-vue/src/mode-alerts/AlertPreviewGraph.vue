<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onScopeDispose, ref, watch } from 'vue'

import {
  initGlobalRefresh,
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
import type { PanelKey } from '@/graphing/types'
import { type Preview, fetchPreview } from '@/mode-alerts/preview-client'
import type { ServiceNameMatch } from '@/mode-alerts/types'
import PreviewGraphFrame from '@/mode-custom-services/PreviewGraphFrame.vue'

const props = defineProps<{
  matchType: ServiceNameMatch
  pattern: string
  timePicker: GlobalTimePickerProps
}>()

const { _t } = usei18n()

const PANEL_KEY: PanelKey = 0
const DEFAULT_FIGURE_WIDTH = 900
const DEBOUNCE_MS = 400

initGlobalRefresh({ intervalSeconds: props.timePicker.refresh.interval_seconds, live: true })
const { range: timePickerRange } = useGlobalTimePickerRange(props.timePicker.default_time_range)
const { requestedTimeRange, setRequestedTimeRange, rangeChange } = useRequestedTimeRange()
const { pauseRefresh, refreshTick, contentReloadPending } = useGlobalRefresh()

const figureWidth = ref(DEFAULT_FIGURE_WIDTH)

const preview = ref<Preview | null>(null)
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
  try {
    const result = await fetchPreview(props.matchType, props.pattern, range, step)
    if (requestId !== requestCounter) {
      return
    }
    preview.value = result
    error.value = null
  } catch (e) {
    if (requestId !== requestCounter) {
      return
    }
    error.value = e instanceof Error ? e.message : String(e)
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

const notice = computed(
  () =>
    fetchNotice.value ??
    previewNotice.value ??
    (isLoading.value || hasPlottableData(metrics.value) ? null : noDataNotice)
)
</script>

<template>
  <PreviewGraphFrame
    v-model:time-picker-range="timePickerRange"
    v-model:figure-width="figureWidth"
    :time-picker="timePicker"
    :title="pattern"
    :metrics="metrics"
    :data-time-range="preview?.time_range"
    :horizontal-lines="preview?.horizontal_lines ?? []"
    :requested-time-range="requestedTimeRange"
    :range-change="rangeChange"
    :panel-key="PANEL_KEY"
    :notice="notice"
    @update:requested-time-range="setRequestedTimeRange($event, PANEL_KEY)"
    @inspect="pauseRefresh"
    @retry="refetch"
  />
</template>
