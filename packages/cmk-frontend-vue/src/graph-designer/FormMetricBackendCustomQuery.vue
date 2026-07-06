<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type GraphLineQueryAttributes } from 'cmk-shared-typing/typescript/graph_designer'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkLabel from '@/components/CmkLabel.vue'
import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import FormMetricBackendConsolidation from '@/metric-backend/FormMetricBackendConsolidation.vue'
import FormMetricNameAutocompleter from '@/metric-backend/FormMetricNameAutocompleter.vue'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  resourceAttributes: GraphLineQueryAttributes
  scopeAttributes: GraphLineQueryAttributes
  dataPointAttributes: GraphLineQueryAttributes
  aggregationLookback: number
  aggregationHistogramPercentile: number
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
const resourceAttributes = defineModel<GraphLineQueryAttributes>('resourceAttributes', {
  default: []
})
const scopeAttributes = defineModel<GraphLineQueryAttributes>('scopeAttributes', {
  default: []
})
const dataPointAttributes = defineModel<GraphLineQueryAttributes>('dataPointAttributes', {
  default: []
})
const aggregationLookback = defineModel<number>('aggregationLookback', {
  required: true
})
const aggregationHistogramPercentile = defineModel<number>('aggregationHistogramPercentile', {
  required: true
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
        v-model:resource-attributes="resourceAttributes"
        v-model:scope-attributes="scopeAttributes"
        v-model:data-point-attributes="dataPointAttributes"
        :metric-name="metricName"
      />
      <FormMetricBackendConsolidation
        v-model:aggregation-lookback="aggregationLookback"
        v-model:aggregation-histogram-percentile="aggregationHistogramPercentile"
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
