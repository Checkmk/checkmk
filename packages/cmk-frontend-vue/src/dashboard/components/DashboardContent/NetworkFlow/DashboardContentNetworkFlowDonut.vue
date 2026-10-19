<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import CmkDonutChart, { type DonutSlice } from '@/dashboard/components/CmkDonutChart'
import { CATEGORICAL_PALETTE } from '@/dashboard/components/CmkDonutChart/colors'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { explicitWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type {
  ComputedNetworkFlowDonut,
  ComputedNetworkFlowDonutSlice,
  NetworkFlowDonutContent
} from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import { formatBytes, previousWindowLabel } from '@/network-flow/format'
import { donutOtherBreakdownSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

import WidgetFigureFrame from '../figures/WidgetFigureFrame.vue'
import type { ContentProps } from '../types.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<NetworkFlowDonutContent>>()

/** The key of the aggregated remainder, which is the one slice with a breakdown. */
const OTHER_SLICE_KEY = 'other'

function buildSlices(computedSlices: ComputedNetworkFlowDonutSlice[], total: number): DonutSlice[] {
  const result: DonutSlice[] = computedSlices.map((slice, index) => ({
    key: `slice-${index}`,
    label: slice.label,
    value: slice.value,
    color: CATEGORICAL_PALETTE[index % CATEGORICAL_PALETTE.length]!,
    previousValue: slice.previous_value
  }))
  // The backend returns the grand total across all entities, so the tail beyond
  // the ranked slices becomes an aggregated "Other" slice. It carries no
  // comparison: the previous grand total is the whole preceding window, and what
  // is left of it after these slices is not the remainder as it stood then.
  const shown = computedSlices.reduce((sum, slice) => sum + slice.value, 0)
  const other = total - shown
  if (other > 0) {
    result.push({
      key: OTHER_SLICE_KEY,
      label: _t('Other'),
      value: other,
      color: 'grey',
      isOther: true
    })
  }
  return result
}

// null when the dashboard does not wire the panels up.
const openOtherBreakdown = inject(donutOtherBreakdownSlideInKey, null)

const { state, retry } = useWidgetData(
  () => dashboardAPI.computeNetworkFlowDonut({ source: explicitWidgetSource(props) }),
  () => [props.content, props.effective_filter_context],
  () => props.tick
)

// The window travels with the slices rather than beside them, so the breakdown
// can only ever be asked about the window the ring on screen was drawn from.
function buildRing(donut: ComputedNetworkFlowDonut) {
  const window = { start: donut.window_from, end: donut.window_until }
  return {
    slices: buildSlices(donut.slices, donut.total),
    window,
    // The comparison is against a window of the same length, so the column says how
    // long that is rather than leaving the reader to guess at the time filter.
    previousLabel: previousWindowLabel(window)
  }
}

const ring = computed(() => (state.value.kind === 'data' ? buildRing(state.value.value) : null))

// The chart reports every slice; only the remainder has something behind it.
function onSliceActivate(key: string): void {
  if (key !== OTHER_SLICE_KEY || openOtherBreakdown === null || ring.value === null) {
    return
  }
  openOtherBreakdown({
    content: props.content,
    context: props.effective_filter_context.filters,
    window: ring.value.window
  })
}
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <div v-if="ring !== null" class="db-content-network-flow-donut__wrapper">
      <CmkDonutChart
        :slices="ring.slices"
        :format-value="formatBytes"
        :legend-mode="content.legend_mode"
        :previous-label="ring.previousLabel"
        @slice-activate="onSliceActivate"
      />
    </div>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-network-flow-donut__wrapper {
  display: flex;
  box-sizing: border-box;
  height: 100%;
  padding: calc(var(--spacing) * 2);
}
</style>
