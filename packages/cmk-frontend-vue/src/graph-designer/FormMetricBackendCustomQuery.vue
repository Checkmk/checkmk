<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type GraphLineQueryAttributes } from 'cmk-shared-typing/typescript/graph_designer'
import type {
  Autocompleter,
  MetricBackendCustomQuery
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkLabel from '@/components/CmkLabel.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'
import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'

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

const validation = ref<string[]>([])

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages | undefined) => {
    if (newValidation && newValidation.length > 0) {
      validation.value = newValidation.map((m) => m.message)
      newValidation.forEach((message) => {
        metricName.value = (message.replacement_value as MetricBackendCustomQuery).metric_name
      })
    }
  }
)

const metricName = defineModel<string | null>('metricName', { default: null })
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

const metricNameAutocompleter = computed<Autocompleter>(() => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_metrics_backend',
    params: {
      strict: true,
      context: metricName.value
        ? {
            metric_name: metricName.value
          }
        : {}
    }
  }
}))
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
          <FormValidation :validation="validation"></FormValidation>
          <FormAutocompleter
            v-model="metricName"
            :autocompleter="metricNameAutocompleter"
            :placeholder="_t('Metric name')"
            :has-error="validation.length > 0"
            @update:model-value="validation = []"
          />
        </td>
      </tr>
      <FormMetricBackendAttributes
        v-model:resource-attributes="resourceAttributes"
        v-model:scope-attributes="scopeAttributes"
        v-model:data-point-attributes="dataPointAttributes"
        :metric-name="metricName"
      />
      <tr>
        <td>{{ _t('Aggregation lookback') }}</td>
        <td>
          <CmkInput v-model="aggregationLookback" type="number" :unit="'s'" field-size="SMALL" />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Percentile (histograms)') }}</td>
        <td>
          <CmkInput v-model="aggregationHistogramPercentile" type="number" :unit="'%'" />
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table {
  border-collapse: separate;
  border-spacing: 5px;
}
</style>
