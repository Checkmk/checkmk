<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import { type ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/graph_designer'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { computed, ref } from 'vue'

import { type ValidationMessages } from '@/form/private/validation'

import {
  DEFAULT_HISTOGRAM_PERCENTILE,
  buildConsolidationFunction,
  consolidationFunctionFromWire
} from '@/graph-designer/consolidation'
import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import FormMetricBackendConsolidation from '@/metric-backend/FormMetricBackendConsolidation.vue'
import FormMetricNameAutocompleter from '@/metric-backend/FormMetricNameAutocompleter.vue'
import type { ConsolidationFunction } from '@/metric-backend/consolidation/types'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  attributeFilter?: AttributeFilter
  consolidationFunction: WireConsolidationFunction
}

const props = defineProps<{
  backendValidation?: ValidationMessages
}>()

// Only the metric name is validated here; the rest moved to FormMetricBackendConsolidation.
const metricNameValidation = ref<string[]>([])

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages | undefined) => {
    metricNameValidation.value = []
    newValidation?.forEach((message) => {
      if (message.location[0] !== 'metric_name') {
        return
      }
      metricNameValidation.value.push(message.message)
      metricName.value = (message.replacement_value as MetricBackendCustomQuery).metric_name
    })
  }
)

const metricName = defineModel<string | null>('metricName', { default: null })
const metricTypes = defineModel<string[]>('metricTypes', { default: () => [] })
const attributeFilter = defineModel<AttributeFilter | undefined>('attributeFilter', {
  default: undefined
})
const consolidation = defineModel<WireConsolidationFunction>('consolidation', { required: true })

const aggregationLookback = computed<number>({
  get: () => consolidation.value.lookback_seconds,
  set: (value) => {
    consolidation.value = { ...consolidation.value, lookback_seconds: value }
  }
})

const aggregationHistogramPercentile = computed<number>({
  get: () =>
    consolidation.value.function === 'histogram_quantile'
      ? consolidation.value.percentile
      : DEFAULT_HISTOGRAM_PERCENTILE,
  set: (value) => {
    if (consolidation.value.function === 'histogram_quantile') {
      consolidation.value = { ...consolidation.value, percentile: value }
    }
  }
})

const consolidationFunction = computed<ConsolidationFunction | null>({
  get: () => consolidationFunctionFromWire(consolidation.value),
  set: (value) => {
    consolidation.value = buildConsolidationFunction(
      value,
      aggregationLookback.value,
      aggregationHistogramPercentile.value
    )
  }
})
</script>

<template>
  <table>
    <tbody>
      <tr>
        <td>
          <CmkLabel>{{ _t('Metric') }}</CmkLabel
          ><CmkLabelRequired />
        </td>
        <td>
          <CmkInlineValidation :validation="metricNameValidation"></CmkInlineValidation>
          <FormMetricNameAutocompleter
            v-model:metric-name="metricName"
            v-model:metric-types="metricTypes"
            :label="_t('Metric name')"
            :placeholder="_t('Metric name')"
            :has-error="metricNameValidation.length > 0"
            @update:metric-name="metricNameValidation = []"
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
        v-model:consolidation-function="consolidationFunction"
        :metric-types="metricTypes"
        :backend-validation="props.backendValidation ?? []"
      />
      <slot name="additional-rows"></slot>
    </tbody>
  </table>
</template>

<style scoped>
table {
  border-collapse: separate;
  border-spacing: 5px;
}

/* Make sure the titles stay aligned with the top of the row for multiline rows */
table td {
  vertical-align: baseline;
}
</style>
