<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed } from 'vue'

import CmkKpiStatCard, {
  type KpiDelta,
  type KpiDeltaConfig,
  type TimestampedSample
} from '@/dashboard/components/CmkKpiStatCard'
import type { NetworkFlowKpiStatCardContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'
import { chartColorCss } from '@/network-flow/colors'

import DashboardContentContainer from '../DashboardContentContainer.vue'
import type { ContentProps } from '../types.ts'
import { useNetworkFlowWidgetData } from './useNetworkFlowWidgetData.ts'

const props = defineProps<ContentProps<NetworkFlowKpiStatCardContent>>()

const { _t } = usei18n()

// How each metric presents itself: the unit formatting follows the metric
// (bytes scale to KB/MB/GB..., counts to K/M/...).
interface MetricPresentation {
  formatter: SIFormatter
}

// Canonical SI byte formatter (base 1000), matching CmkRankedTable: 801_840_000_000 → "801.84 GB".
const BYTES = new SIFormatter('B', { type: 'strict', digits: 2 })
// Unitless activity counts: 532 → "532", 4_300 → "4.3 K".
const COUNT = new SIFormatter('', { type: 'strict', digits: 1 })
// Rates in bits per second, in the mockups' unit style: 3_200_000_000 → "3.20 Gbps".
const THROUGHPUT = new SIFormatter('bps', { type: 'strict', digits: 2 })

const METRIC_PRESENTATION: Record<NetworkFlowKpiStatCardContent['metric'], MetricPresentation> = {
  total_bytes: { formatter: BYTES },
  ingress_bytes: { formatter: BYTES },
  egress_bytes: { formatter: BYTES },
  active_hosts: { formatter: COUNT },
  total_flows: { formatter: COUNT },
  active_asn: { formatter: COUNT },
  peak_throughput: { formatter: THROUGHPUT },
  avg_throughput: { formatter: THROUGHPUT },
  tracked_hosts: { formatter: COUNT }
}

interface CardData {
  value: string
  unit: string | undefined
  delta: KpiDelta | undefined
  series: TimestampedSample[]
}

const presentation = computed(() => METRIC_PRESENTATION[props.content.metric])

// Every metric's headline `value` is a window-wide aggregate (a sum, or a
// deduplicated count) rather than a live reading, so the delta compares it
// against `previous_value`, an equally-aggregated total for the prior window -
// comparing two single `series` buckets (CmkKpiStatCard's own comparisonBasis)
// would put the delta on a different scale than the headline entirely.
function buildDelta(value: number, previousValue: number): KpiDelta | undefined {
  // A delta needs a positive reference: a zero previous window means "no
  // comparison possible", not an infinite increase.
  if (!props.content.show_delta || previousValue <= 0) {
    return undefined
  }
  const ratio = (value - previousValue) / previousValue
  return {
    percent: `${Math.abs(ratio * 100).toFixed(1)}%`,
    up: ratio >= 0,
    comparisonText: _t('vs. %{previousValue} prev. window', {
      previousValue: presentation.value.formatter.render(previousValue)
    })
  }
}

function buildCardData(
  value: number,
  previousValue: number,
  series: TimestampedSample[]
): CardData {
  // The card renders the value and its unit in different sizes, so the
  // formatter's "801.84 GB" is split at the first space; plain counts
  // ("532") have no unit part.
  const rendered = presentation.value.formatter.render(value)
  const spaceIndex = rendered.indexOf(' ')
  return {
    value: spaceIndex === -1 ? rendered : rendered.slice(0, spaceIndex),
    unit: spaceIndex === -1 ? undefined : rendered.slice(spaceIndex + 1),
    delta: buildDelta(value, previousValue),
    series
  }
}

const { data, error } = useNetworkFlowWidgetData(
  () =>
    dashboardAPI.computeNetworkFlowKpiStatCardData(
      props.content,
      props.effective_filter_context.filters
    ),
  (response) =>
    buildCardData(response.value.value, response.value.previous_value, response.value.series),
  () => ({ filters: props.effective_filter_context.filters, content: props.content })
)

const deltaConfig = computed<KpiDeltaConfig>(() => ({
  show: props.content.show_delta,
  override: data.value?.delta,
  fromCaller: true
}))
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-network-flow-kpi-stat-card__wrapper">
      <div v-if="error" class="db-content-network-flow-kpi-stat-card__error">
        <CmkAlertBox :variant="error.variant">{{ error.message }}</CmkAlertBox>
      </div>
      <CmkLoading v-else-if="data === undefined" />
      <CmkKpiStatCard
        v-else
        :value="data.value"
        :unit="data.unit"
        :delta="deltaConfig"
        :series="data.series"
        :color="chartColorCss(content.accent)"
        spark-height-mode="band"
      />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
/* No padding: the card insets its own content and is full-bleed otherwise, so
   its spark line reaches the widget's edges. */
.db-content-network-flow-kpi-stat-card__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
}

.db-content-network-flow-kpi-stat-card__error {
  margin: auto;
  max-width: 90%;
}
</style>
