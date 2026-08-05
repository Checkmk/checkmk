<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { computed, ref, watch } from 'vue'

import type { ValidationMessages } from '@/form'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import {
  METRIC_TYPES,
  consolidationFunctionOf,
  defaultFunction
} from '@/metric-backend/consolidation/types'
import type {
  AllowedFunctions,
  ConsolidationFunction,
  ConsolidationModel,
  MetricType
} from '@/metric-backend/consolidation/types'

const { _t } = usei18n()

// Offer only the functions the backend implements.
const SUPPORTED_FUNCTIONS: AllowedFunctions = {
  gauge: ['gauge_last', 'gauge_max', 'gauge_avg', 'gauge_min'],
  sum: ['sum_rate', 'sum_last_raw', 'sum_delta'],
  histogram: [
    'histogram_preserve',
    'histogram_quantile',
    'histogram_count_delta',
    'histogram_count_rate',
    'histogram_sum_rate',
    'histogram_sum_delta',
    'histogram_fraction_below',
    'histogram_fraction_between',
    'histogram_sum_raw'
  ]
}

// Fall back to histogram before the type resolves so the percentile stays reachable.
const FALLBACK_TYPE: MetricType = 'histogram'

const props = defineProps<{
  metricTypes: string[]
}>()

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })
const aggregationLookback = defineModel<number>('aggregationLookback', { required: true })
const aggregationHistogramPercentile = defineModel<number>('aggregationHistogramPercentile', {
  required: true
})
const aggregationHistogramThresholdForFractionBelow = defineModel<number>(
  'aggregationHistogramThresholdForFractionBelow',
  { required: true }
)
const aggregationHistogramLowerThresholdForFractionBetween = defineModel<number>(
  'aggregationHistogramLowerThresholdForFractionBetween',
  { required: true }
)
const aggregationHistogramUpperThresholdForFractionBetween = defineModel<number>(
  'aggregationHistogramUpperThresholdForFractionBetween',
  { required: true }
)
const consolidationFunction = defineModel<ConsolidationFunction | null>('consolidationFunction', {
  default: null
})

function isMetricType(value: string): value is MetricType {
  return (METRIC_TYPES as readonly string[]).includes(value)
}

const availableTypes = computed<MetricType[]>(() => props.metricTypes.filter(isMetricType))

// A previously persisted function pick wins; only a line without one yet (new or old
// saved data) falls back to deriving from the metric's first available type.
function paramsFor(fn: ConsolidationFunction): ConsolidationModel['params'] {
  switch (fn.function) {
    case 'histogram_quantile':
      return { quantile: aggregationHistogramPercentile.value / 100 }
    case 'histogram_fraction_below':
      return { fractionBelowThreshold: aggregationHistogramThresholdForFractionBelow.value }
    case 'histogram_fraction_between':
      return {
        fractionLowerThreshold: aggregationHistogramLowerThresholdForFractionBetween.value,
        fractionUpperThreshold: aggregationHistogramUpperThresholdForFractionBetween.value
      }
    default:
      return {}
  }
}

function buildModel(): ConsolidationModel {
  const fn =
    consolidationFunction.value ??
    defaultFunction(availableTypes.value[0] ?? FALLBACK_TYPE, SUPPORTED_FUNCTIONS)
  return {
    ...fn,
    params: paramsFor(fn),
    lookbackSeconds: aggregationLookback.value
  }
}

const model = ref<ConsolidationModel>(buildModel())

// Mirror the editable pill values back to the persisted fields. Each param
// belongs to its own function only, so other types leave it untouched.
watch(
  model,
  (value) => {
    if (value.lookbackSeconds !== aggregationLookback.value) {
      aggregationLookback.value = value.lookbackSeconds
    }
    if (value.function === 'histogram_quantile' && value.params.quantile !== undefined) {
      const percentile = value.params.quantile * 100
      if (percentile !== aggregationHistogramPercentile.value) {
        aggregationHistogramPercentile.value = percentile
      }
    }
    if (
      value.function === 'histogram_fraction_below' &&
      value.params.fractionBelowThreshold !== undefined &&
      value.params.fractionBelowThreshold !== aggregationHistogramThresholdForFractionBelow.value
    ) {
      aggregationHistogramThresholdForFractionBelow.value = value.params.fractionBelowThreshold
    }
    if (value.function === 'histogram_fraction_between') {
      if (
        value.params.fractionLowerThreshold !== undefined &&
        value.params.fractionLowerThreshold !==
          aggregationHistogramLowerThresholdForFractionBetween.value
      ) {
        aggregationHistogramLowerThresholdForFractionBetween.value =
          value.params.fractionLowerThreshold
      }
      if (
        value.params.fractionUpperThreshold !== undefined &&
        value.params.fractionUpperThreshold !==
          aggregationHistogramUpperThresholdForFractionBetween.value
      ) {
        aggregationHistogramUpperThresholdForFractionBetween.value =
          value.params.fractionUpperThreshold
      }
    }
    const fn = consolidationFunctionOf(value)
    if (
      fn.type !== consolidationFunction.value?.type ||
      fn.function !== consolidationFunction.value?.function
    ) {
      consolidationFunction.value = fn
    }
  },
  { deep: true }
)

const validationMessages = ref<string[]>([])

const VALIDATED_LOCATIONS = [
  'aggregation_lookback',
  'aggregation_histogram_percentile',
  'aggregation_histogram_threshold_for_fraction_below',
  'aggregation_histogram_lower_threshold_for_fraction_between',
  'aggregation_histogram_upper_threshold_for_fraction_between'
] as const

immediateWatch(
  () => backendValidation.value,
  (newValidation: ValidationMessages | undefined) => {
    validationMessages.value = []
    newValidation?.forEach((message) => {
      const location = message.location[0]
      if (!(VALIDATED_LOCATIONS as readonly string[]).includes(location ?? '')) {
        return
      }
      validationMessages.value.push(message.message)
      const replacement = message.replacement_value as MetricBackendCustomQuery
      switch (location) {
        case 'aggregation_lookback':
          aggregationLookback.value = replacement.aggregation_lookback
          break
        case 'aggregation_histogram_percentile':
          aggregationHistogramPercentile.value = replacement.aggregation_histogram_percentile
          break
        case 'aggregation_histogram_threshold_for_fraction_below':
          aggregationHistogramThresholdForFractionBelow.value =
            replacement.aggregation_histogram_threshold_for_fraction_below
          break
        case 'aggregation_histogram_lower_threshold_for_fraction_between':
          aggregationHistogramLowerThresholdForFractionBetween.value =
            replacement.aggregation_histogram_lower_threshold_for_fraction_between
          break
        case 'aggregation_histogram_upper_threshold_for_fraction_between':
          aggregationHistogramUpperThresholdForFractionBetween.value =
            replacement.aggregation_histogram_upper_threshold_for_fraction_between
          break
      }
    })
    if (validationMessages.value.length > 0) {
      model.value = buildModel()
    }
  }
)
</script>

<template>
  <tr>
    <td class="metric-backend-form-metric-backend-consolidation__label-cell">
      {{ _t('Consolidation') }}
    </td>
    <td>
      <CmkInlineValidation :validation="validationMessages" />
      <FormConsolidation
        v-model="model"
        :available-types="availableTypes"
        :allowed-functions="SUPPORTED_FUNCTIONS"
      />
    </td>
  </tr>
</template>

<style scoped>
.metric-backend-form-metric-backend-consolidation__label-cell {
  vertical-align: top;
}
</style>
