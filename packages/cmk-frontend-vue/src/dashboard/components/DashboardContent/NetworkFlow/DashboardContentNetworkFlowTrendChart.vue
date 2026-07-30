<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed, inject } from 'vue'

import type { NetworkFlowTrendChartContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import CmkTrendChart from '@/network-flow/CmkTrendChart'
import { autonomousSystemSlideInKey } from '@/network-flow/slide-ins/injectionKeys'

import DashboardContentContainer from '../DashboardContentContainer.vue'
import type { ContentProps } from '../types.ts'
import { useNetworkFlowWidgetData } from './useNetworkFlowWidgetData.ts'

const props = defineProps<ContentProps<NetworkFlowTrendChartContent>>()

// null when the dashboard does not wire it up; series names then stay plain text.
const openAutonomousSystemSlideIn = inject(autonomousSystemSlideInKey, null)

// The autonomous_systems dimension labels its series "AS<n>"; make those open
// the AS detail slide-in.
const clickableSeries = computed(
  () => props.content.dimension === 'autonomous_systems' && openAutonomousSystemSlideIn !== null
)

function onSeriesClick(name: string): void {
  if (!openAutonomousSystemSlideIn) {
    return
  }
  const asn = Number(name.replace(/^AS/, ''))
  if (!Number.isNaN(asn)) {
    openAutonomousSystemSlideIn(asn)
  }
}

// The trend series are per-minute throughput values; format both the axis ticks
// and the legend statistics as bits per second, in the mockups' unit style
// (3_200_000_000 → "3.20 Gbps").
const THROUGHPUT = new SIFormatter('bps', { type: 'strict', digits: 2 })
const formatValue = (value: number): string => THROUGHPUT.render(value)

const { data: series, error } = useNetworkFlowWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowTrendChartData(
      props.content,
      props.effective_filter_context.filters
    ),
  (response) =>
    response.value.series.map((item) => ({
      name: item.name,
      dataPoints: item.data_points,
      minimum: item.minimum,
      maximum: item.maximum,
      average: item.average,
      last: item.last
    })),
  () => ({ filters: props.effective_filter_context.filters, content: props.content })
)
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-network-flow-trend-chart__wrapper">
      <div v-if="error" class="db-content-network-flow-trend-chart__error">
        <CmkAlertBox :variant="error.variant">{{ error.message }}</CmkAlertBox>
      </div>
      <CmkLoading v-else-if="series === undefined" />
      <CmkTrendChart
        v-else
        :series="series"
        :display-mode="content.display_mode"
        :format-value="formatValue"
        :clickable-series="clickableSeries"
        @series-click="onSeriesClick"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-network-flow-trend-chart__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
  padding: calc(var(--spacing) * 2);
}

.db-content-network-flow-trend-chart__error {
  margin: auto;
  max-width: 90%;
}
</style>
