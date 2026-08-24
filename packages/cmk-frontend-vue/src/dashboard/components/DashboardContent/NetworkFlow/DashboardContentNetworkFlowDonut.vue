<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject } from 'vue'

import type {
  ComputedNetworkFlowDonutSlice,
  NetworkFlowDonutContent
} from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'
import { CATEGORICAL_PALETTE } from '@/network-flow/colors'
import { formatBytes, previousWindowLabel } from '@/network-flow/format'
import { donutOtherBreakdownSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

import DashboardContentContainer from '../DashboardContentContainer.vue'
import type { ContentProps } from '../types.ts'
import { useNetworkFlowWidgetData } from './useNetworkFlowWidgetData.ts'

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

// The window travels with the slices rather than beside them, so the breakdown
// can only ever be asked about the window the ring on screen was drawn from.
const { data, error } = useNetworkFlowWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowDonutData(props.content, props.effective_filter_context.filters),
  (response) => ({
    slices: buildSlices(response.value.slices, response.value.total),
    window: { start: response.value.window_from, end: response.value.window_until }
  }),
  () => ({ filters: props.effective_filter_context.filters, content: props.content })
)

const slices = computed(() => data.value?.slices)

// The comparison is against a window of the same length, so the column says how
// long that is rather than leaving the reader to guess at the time filter.
const previousLabel = computed(() =>
  data.value === undefined ? undefined : previousWindowLabel(data.value.window)
)

// The chart reports every slice; only the remainder has something behind it.
function onSliceActivate(key: string): void {
  const loaded = data.value
  if (key !== OTHER_SLICE_KEY || openOtherBreakdown === null || loaded === undefined) {
    return
  }
  openOtherBreakdown({
    content: props.content,
    context: props.effective_filter_context.filters,
    window: loaded.window
  })
}
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-network-flow-donut__wrapper">
      <div v-if="error" class="db-content-network-flow-donut__error">
        <CmkAlertBox :variant="error.variant">{{ error.message }}</CmkAlertBox>
      </div>
      <CmkLoading v-else-if="slices === undefined" />
      <CmkDonutChart
        v-else
        :slices="slices"
        :format-value="formatBytes"
        :legend-mode="content.legend_mode"
        :previous-label="previousLabel"
        @slice-activate="onSliceActivate"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-network-flow-donut__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
  padding: calc(var(--spacing) * 2);
}

.db-content-network-flow-donut__error {
  margin: auto;
  max-width: 90%;
}
</style>
