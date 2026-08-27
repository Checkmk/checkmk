<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { computed, ref, watch } from 'vue'

import type { ValidationMessages } from '@/form'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import {
  DEFAULT_QUANTILE,
  METRIC_TYPES,
  consolidationFunctionOf,
  defaultFunction
} from '@/metric-backend/consolidation/types'
import type {
  ConsolidationFunction,
  ConsolidationModel,
  MetricType
} from '@/metric-backend/consolidation/types'

// Fall back to histogram before the type resolves so the percentile stays reachable.
const FALLBACK_TYPE: MetricType = 'histogram'

const props = defineProps<{
  label: TranslatedString
  metricTypes: string[]
  metricName: string | null
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
    consolidationFunction.value ?? defaultFunction(availableTypes.value[0] ?? FALLBACK_TYPE)
  return {
    ...fn,
    params: paramsFor(fn),
    lookbackSeconds: aggregationLookback.value
  }
}

const model = ref<ConsolidationModel>(buildModel())

// name and resolved types settle in an unpredictable order, so both watches drive the reset.
const pendingMetricReset = ref(false)

function applyPendingReset(typesJustResolved: boolean): void {
  const types = availableTypes.value
  // Empty is "not resolved yet", not "no types": wait for the new metric's real list.
  if (!pendingMetricReset.value || types.length === 0) {
    return
  }
  const stillFits = types.includes(model.value.type)
  if (!stillFits) {
    const fn = defaultFunction(types[0]!)
    const params = fn.function === 'histogram_quantile' ? { quantile: DEFAULT_QUANTILE } : {}
    model.value = { ...model.value, ...fn, params }
  }
  if (typesJustResolved || !stillFits) {
    pendingMetricReset.value = false
  }
}

// Non-immediate: the initial stored name never fires, so a load keeps its consolidation as is.
watch(
  () => props.metricName,
  () => {
    pendingMetricReset.value = true
    applyPendingReset(false)
  }
)
watch(availableTypes, () => applyPendingReset(true))

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
  <div>
    <CmkInlineValidation :validation="validationMessages" />
    <FormConsolidation v-model="model" :available-types="availableTypes" :label="props.label" />
  </div>
</template>
