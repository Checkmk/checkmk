<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import FormMetricBackendConsolidation from '@/metric-backend/FormMetricBackendConsolidation.vue'
import FormMetricNameAutocompleter from '@/metric-backend/FormMetricNameAutocompleter.vue'
import type { ConsolidationFunction } from '@/metric-backend/consolidation/types'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftMetricBackendItem } from '../../drafts'
import type { MetricBackendItem } from '../../types'

const { item, store } = defineProps<{
  item: DraftMetricBackendItem
  store: GraphItemsStore
}>()

const { _t } = usei18n()

const DEFAULT_HISTOGRAM_PERCENTILE = 90
const DEFAULT_THRESHOLD_FOR_FRACTION_BELOW = 0
const DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN = 0
const DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN = 100

type Consolidation = MetricBackendItem['consolidation_function']

// The picker edits function, lookback and percentile independently and speaks the grouped
// {type, function} shape, while the item stores the flat engine union — so map between them
// (rebuilding the whole value, never spreading, which would decorrelate the union).
function toStored(
  consolidationFunction: ConsolidationFunction,
  lookbackSeconds: number,
  percentile: number,
  thresholdForFractionBelow: number,
  lowerThresholdForFractionBetween: number,
  upperThresholdForFractionBetween: number
): Consolidation {
  switch (consolidationFunction?.function) {
    case 'gauge_max':
      return { type: 'gauge_max', lookback_seconds: lookbackSeconds }
    case 'gauge_avg':
      return { type: 'gauge_avg', lookback_seconds: lookbackSeconds }
    case 'gauge_min':
      return { type: 'gauge_min', lookback_seconds: lookbackSeconds }
    case 'sum_rate':
      return { type: 'sum_rate', lookback_seconds: lookbackSeconds }
    case 'sum_last_raw':
      return { type: 'sum_last_raw', lookback_seconds: lookbackSeconds }
    case 'sum_delta':
      return { type: 'sum_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_quantile':
      return { type: 'histogram_quantile', lookback_seconds: lookbackSeconds, percentile }
    case 'histogram_fraction_below':
      return {
        type: 'histogram_fraction_below',
        lookback_seconds: lookbackSeconds,
        threshold: thresholdForFractionBelow
      }
    case 'histogram_fraction_between':
      return {
        type: 'histogram_fraction_between',
        lookback_seconds: lookbackSeconds,
        lower_threshold: lowerThresholdForFractionBetween,
        upper_threshold: upperThresholdForFractionBetween
      }
    case 'histogram_count_delta':
      return { type: 'histogram_count_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_count_rate':
      return { type: 'histogram_count_rate', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_rate':
      return { type: 'histogram_sum_rate', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_delta':
      return { type: 'histogram_sum_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_raw':
      return { type: 'histogram_sum_raw', lookback_seconds: lookbackSeconds }
    case 'gauge_last':
    default:
      return { type: 'gauge_last', lookback_seconds: lookbackSeconds }
  }
}

function toPicker(consolidation: Consolidation): ConsolidationFunction {
  switch (consolidation.type) {
    case 'gauge_last':
    case 'gauge_max':
    case 'gauge_avg':
    case 'gauge_min':
      return { type: 'gauge', function: consolidation.type }
    case 'sum_rate':
    case 'sum_last_raw':
    case 'sum_delta':
      return { type: 'sum', function: consolidation.type }
    case 'histogram_quantile':
    case 'histogram_count_delta':
    case 'histogram_count_rate':
    case 'histogram_sum_rate':
    case 'histogram_sum_delta':
    case 'histogram_sum_raw':
    case 'histogram_fraction_below':
    case 'histogram_fraction_between':
      return { type: 'histogram', function: consolidation.type }
  }
}

function withConsolidation(consolidation: Consolidation): void {
  store.replace({ ...item, consolidation_function: consolidation })
}

const metricTypes = ref<string[]>([])

const metricName = computed<string | null>({
  get: () => item.metric_name,
  set: (value) => store.replace({ ...item, metric_name: value })
})

const attributeFilter = computed<AttributeFilter | undefined>({
  get: () => item.attribute_filter,
  set: (value) =>
    store.replace({ ...item, attribute_filter: value ?? { type: 'and', conjuncts: [] } })
})

function storeCurrentWith(overrides: {
  lookbackSeconds?: number
  percentile?: number
  thresholdForFractionBelow?: number
  lowerThresholdForFractionBetween?: number
  upperThresholdForFractionBetween?: number
  consolidationFunction?: ConsolidationFunction
}): void {
  withConsolidation(
    toStored(
      overrides.consolidationFunction ?? consolidationFunction.value,
      overrides.lookbackSeconds ?? aggregationLookback.value,
      overrides.percentile ?? aggregationHistogramPercentile.value,
      overrides.thresholdForFractionBelow ?? aggregationHistogramThresholdForFractionBelow.value,
      overrides.lowerThresholdForFractionBetween ??
        aggregationHistogramLowerThresholdForFractionBetween.value,
      overrides.upperThresholdForFractionBetween ??
        aggregationHistogramUpperThresholdForFractionBetween.value
    )
  )
}

const aggregationLookback = computed<number>({
  get: () => item.consolidation_function.lookback_seconds,
  set: (value) => storeCurrentWith({ lookbackSeconds: value })
})

const aggregationHistogramPercentile = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_quantile'
      ? item.consolidation_function.percentile
      : DEFAULT_HISTOGRAM_PERCENTILE,
  set: (value) => storeCurrentWith({ percentile: value })
})

const aggregationHistogramThresholdForFractionBelow = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_below'
      ? item.consolidation_function.threshold
      : DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  set: (value) => storeCurrentWith({ thresholdForFractionBelow: value })
})

const aggregationHistogramLowerThresholdForFractionBetween = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_between'
      ? item.consolidation_function.lower_threshold
      : DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => storeCurrentWith({ lowerThresholdForFractionBetween: value })
})

const aggregationHistogramUpperThresholdForFractionBetween = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_between'
      ? item.consolidation_function.upper_threshold
      : DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => storeCurrentWith({ upperThresholdForFractionBetween: value })
})

const consolidationFunction = computed<ConsolidationFunction>({
  get: () => toPicker(item.consolidation_function),
  set: (value) => storeCurrentWith({ consolidationFunction: value })
})
</script>

<template>
  <table class="graphing-metric-backend-form">
    <tbody>
      <tr>
        <td class="graphing-metric-backend-form__label-cell">
          <CmkLabel>{{ _t('Metric') }}</CmkLabel
          ><CmkLabelRequired />
        </td>
        <td>
          <FormMetricNameAutocompleter
            v-model:metric-name="metricName"
            v-model:metric-types="metricTypes"
            :placeholder="_t('Metric name')"
            :label="_t('Metric name')"
          />
        </td>
      </tr>
      <FormMetricBackendAttributes
        v-model:attribute-filter="attributeFilter"
        :metric-name="metricName"
      />
      <FormMetricBackendConsolidation
        v-model:aggregation-lookback="aggregationLookback"
        v-model:aggregation-histogram-percentile="aggregationHistogramPercentile"
        v-model:aggregation-histogram-threshold-for-fraction-below="
          aggregationHistogramThresholdForFractionBelow
        "
        v-model:aggregation-histogram-lower-threshold-for-fraction-between="
          aggregationHistogramLowerThresholdForFractionBetween
        "
        v-model:aggregation-histogram-upper-threshold-for-fraction-between="
          aggregationHistogramUpperThresholdForFractionBetween
        "
        v-model:consolidation-function="consolidationFunction"
        :metric-types="metricTypes"
      />
    </tbody>
  </table>
</template>

<style scoped>
.graphing-metric-backend-form {
  padding: var(--dimension-7);
  border-collapse: separate;
  border-spacing: var(--dimension-4);
}

.graphing-metric-backend-form__label-cell {
  vertical-align: baseline;
  white-space: nowrap;
}
</style>
