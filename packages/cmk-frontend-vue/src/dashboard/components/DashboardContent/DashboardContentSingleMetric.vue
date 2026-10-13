<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { computed } from 'vue'

import CmkKpiStatCard, {
  type KpiDeltaConfig,
  type KpiState
} from '@/dashboard/components/CmkKpiStatCard'
import { useRangedComputedWidget } from '@/dashboard/composables/useComputedWidget'
import { contextualLinkUrl } from '@/dashboard/lib/contextualLinkUrl'
import type { ComputedSingleMetric, SingleMetricContent } from '@/dashboard/types/widget.ts'
import { dashboardAPI } from '@/dashboard/utils.ts'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps<SingleMetricContent>>()
const { state, retry } = useRangedComputedWidget(
  props,
  dashboardAPI.computeSingleMetric,
  () => props.content.time_range !== 'current' && props.content.time_range.window === 'dashboard'
)

function href(metric: ComputedSingleMetric): string | undefined {
  const link = metric.links[0]
  const properties = metric.link_properties.links[0]
  if (link === undefined || properties === undefined) {
    return undefined
  }
  return contextualLinkUrl(link, properties, props.effective_filter_context.filters)
}

function kpiState(metric: ComputedSingleMetric): KpiState | undefined {
  return metric.state
    ? { severity: metric.state.severity, tintBackground: metric.state.tint_background }
    : undefined
}

const deltaConfig = computed<KpiDeltaConfig>(() => ({ show: props.content.show_delta }))

// The series is raw, so whatever the card derives from it (the delta's comparison
// value, a hovered sample) is scaled like the headline value. The backend sends the
// unit already converted to the user's temperature unit, so the one given here is moot.
function formatValue(metric: ComputedSingleMetric): (value: number) => string {
  const formatter = userSpecificUnit(metric.unit_format, 'celsius').formatter
  return (value) => formatter.render(value)
}
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value }">
      <CmkKpiStatCard
        :title="effectiveTitle"
        :value="value.value"
        :unit="value.unit ?? undefined"
        :series="value.series"
        :color="value.color"
        :state="kpiState(value)"
        :range-limits="value.range_limits ?? undefined"
        :range="value.range ?? undefined"
        :stale="value.stale"
        :href="href(value)"
        :format-value="formatValue(value)"
        :spark-height-mode="content.spark_height_mode"
        :delta="deltaConfig"
      />
    </template>
  </WidgetFigureFrame>
</template>
