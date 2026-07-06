<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import type { ValidationMessages } from '@/form'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import { METRIC_TYPES, defaultFunction } from '@/metric-backend/consolidation/types'
import type {
  AllowedFunctions,
  ConsolidationModel,
  MetricType
} from '@/metric-backend/consolidation/types'

const { _t } = usei18n()

// The backend implements one consolidation function per type today; offer only that one.
const SUPPORTED_FUNCTIONS: AllowedFunctions = {
  gauge: ['last_value'],
  sum: ['rate'],
  histogram: ['quantile']
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

function isMetricType(value: string): value is MetricType {
  return (METRIC_TYPES as readonly string[]).includes(value)
}

const availableTypes = computed<MetricType[]>(() => props.metricTypes.filter(isMetricType))

// Type and function are derived for display; only lookback and the percentile are persisted.
function buildModel(): ConsolidationModel {
  const type = availableTypes.value[0] ?? FALLBACK_TYPE
  const fn = defaultFunction(type, SUPPORTED_FUNCTIONS)
  return {
    type,
    function: fn,
    params: fn === 'quantile' ? { quantile: aggregationHistogramPercentile.value / 100 } : {},
    lookbackSeconds: aggregationLookback.value
  }
}

const model = ref<ConsolidationModel>(buildModel())

// Mirror the editable pill values back to the persisted floats. The percentile
// belongs to the quantile function only, so other types leave it untouched.
watch(
  model,
  (value) => {
    if (value.lookbackSeconds !== aggregationLookback.value) {
      aggregationLookback.value = value.lookbackSeconds
    }
    if (value.function === 'quantile' && value.params.quantile !== undefined) {
      const percentile = value.params.quantile * 100
      if (percentile !== aggregationHistogramPercentile.value) {
        aggregationHistogramPercentile.value = percentile
      }
    }
  },
  { deep: true }
)

const validationMessages = ref<string[]>([])

immediateWatch(
  () => backendValidation.value,
  (newValidation: ValidationMessages | undefined) => {
    validationMessages.value = []
    newValidation?.forEach((message) => {
      const location = message.location[0]
      if (location !== 'aggregation_lookback' && location !== 'aggregation_histogram_percentile') {
        return
      }
      validationMessages.value.push(message.message)
      const replacement = message.replacement_value as MetricBackendCustomQuery
      if (location === 'aggregation_lookback') {
        aggregationLookback.value = replacement.aggregation_lookback
      } else {
        aggregationHistogramPercentile.value = replacement.aggregation_histogram_percentile
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
