<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { TelemetryMetricsCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { computed, ref, watch } from 'vue'

import type { ValidationMessages } from '@/form'

import FormConsolidation from '@/telemetry-metrics/consolidation/FormConsolidation.vue'
import {
  DEFAULT_QUANTILE,
  METRIC_TYPES,
  defaultFunction
} from '@/telemetry-metrics/consolidation/types'
import type { ConsolidationModel, MetricType } from '@/telemetry-metrics/consolidation/types'

const props = defineProps<{
  label: TranslatedString
  metricTypes: string[]
  metricName: string | null
}>()

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })
const consolidation = defineModel<ConsolidationModel>('consolidation', { required: true })

function isMetricType(value: string): value is MetricType {
  return (METRIC_TYPES as readonly string[]).includes(value)
}

const availableTypes = computed<MetricType[]>(() => props.metricTypes.filter(isMetricType))

function copyOf(value: ConsolidationModel): ConsolidationModel {
  return { ...value, params: { ...value.params } }
}

// The draft the widget edits, not a view of the stored value: a blank parameter cannot be
// stored, so reading the model back would refill an input the user has just cleared.
const model = ref<ConsolidationModel>(copyOf(consolidation.value))

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

// One write for the whole value: a parent rebuilds what it stores from every part, so a
// function and its parameters arriving separately would each be paired with a stale sibling.
watch(
  model,
  (value) => {
    consolidation.value = copyOf(value)
  },
  { deep: true }
)

const validationMessages = ref<string[]>([])

function withReplacement(
  current: ConsolidationModel,
  location: string | undefined,
  replacement: TelemetryMetricsCustomQuery
): ConsolidationModel {
  const withParams = (params: ConsolidationModel['params']): ConsolidationModel => ({
    ...current,
    params: { ...current.params, ...params }
  })
  switch (location) {
    case 'aggregation_lookback':
      return { ...current, lookbackSeconds: replacement.aggregation_lookback }
    case 'aggregation_histogram_percentile':
      return current.function === 'histogram_quantile'
        ? withParams({ quantile: replacement.aggregation_histogram_percentile / 100 })
        : current
    case 'aggregation_histogram_threshold_for_fraction_below':
      return current.function === 'histogram_fraction_below'
        ? withParams({
            fractionBelowThreshold: replacement.aggregation_histogram_threshold_for_fraction_below
          })
        : current
    case 'aggregation_histogram_lower_threshold_for_fraction_between':
      return current.function === 'histogram_fraction_between'
        ? withParams({
            fractionLowerThreshold:
              replacement.aggregation_histogram_lower_threshold_for_fraction_between
          })
        : current
    case 'aggregation_histogram_upper_threshold_for_fraction_between':
      return current.function === 'histogram_fraction_between'
        ? withParams({
            fractionUpperThreshold:
              replacement.aggregation_histogram_upper_threshold_for_fraction_between
          })
        : current
    default:
      return current
  }
}

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
      model.value = withReplacement(
        model.value,
        location,
        message.replacement_value as TelemetryMetricsCustomQuery
      )
    })
  }
)
</script>

<template>
  <div>
    <CmkInlineValidation :validation="validationMessages" />
    <FormConsolidation v-model="model" :available-types="availableTypes" :label="props.label" />
  </div>
</template>
