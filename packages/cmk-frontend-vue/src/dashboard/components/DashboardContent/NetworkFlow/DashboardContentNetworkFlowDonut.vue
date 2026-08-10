<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { NetworkFlowDonutContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'
import { CATEGORICAL_PALETTE } from '@/network-flow/colors'
import { formatBytes } from '@/network-flow/format'

import DashboardContentContainer from '../DashboardContentContainer.vue'
import type { ContentProps } from '../types.ts'
import { useNetworkFlowWidgetData } from './useNetworkFlowWidgetData.ts'

const { _t } = usei18n()
const props = defineProps<ContentProps<NetworkFlowDonutContent>>()

function buildSlices(
  computedSlices: { label: string; value: number }[],
  total: number
): DonutSlice[] {
  const result: DonutSlice[] = computedSlices.map((slice, index) => ({
    key: `slice-${index}`,
    label: slice.label,
    value: slice.value,
    color: CATEGORICAL_PALETTE[index % CATEGORICAL_PALETTE.length]!
  }))
  // The backend returns the grand total across all entities, so the tail beyond
  // the ranked slices becomes an aggregated "Other" slice.
  const shown = computedSlices.reduce((sum, slice) => sum + slice.value, 0)
  const other = total - shown
  if (other > 0) {
    result.push({ key: 'other', label: _t('Other'), value: other, color: 'grey' })
  }
  return result
}

const { data: slices, error } = useNetworkFlowWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowDonutData(props.content, props.effective_filter_context.filters),
  (response) => buildSlices(response.value.slices, response.value.total),
  () => ({ filters: props.effective_filter_context.filters, content: props.content })
)
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
      <CmkDonutChart v-else :slices="slices" :format-value="formatBytes" />
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
