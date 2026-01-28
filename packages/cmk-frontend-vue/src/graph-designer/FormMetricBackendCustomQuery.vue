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

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'
import CmkTimeSpan from '@/components/user-input/CmkTimeSpan/CmkTimeSpan.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'
import FormHelp from '@/form/private/FormHelp.vue'
import { type ValidationMessages } from '@/form/private/validation'

import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'

const { _t } = usei18n()

const AGGREGATION_LOOKBACK_HELP_TEXT = _t(
  'The time window used to aggregate data for each point on the chart.<ul>' +
    '<li>Sum metrics: Calculates the rate per second over this range.</li>' +
    '<li>Histogram metrics: Uses all samples in this range to calculate percentiles (e.g. p99).</li></ul>'
)

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

enum ValidationLocation {
  METRIC_NAME = 'metric_name',
  AGGREGATION_LOOKBACK = 'aggregation_lookback',
  AGGREGATION_HISTOGRAM_PERCENTILE = 'aggregation_histogram_percentile'
}

type ValidationByLocation = {
  [ValidationLocation.METRIC_NAME]: string[]
  [ValidationLocation.AGGREGATION_LOOKBACK]: string[]
  [ValidationLocation.AGGREGATION_HISTOGRAM_PERCENTILE]: string[]
}

const validationByLocation = ref<ValidationByLocation>({
  [ValidationLocation.METRIC_NAME]: [],
  [ValidationLocation.AGGREGATION_LOOKBACK]: [],
  [ValidationLocation.AGGREGATION_HISTOGRAM_PERCENTILE]: []
})

immediateWatch(
  () => props.backendValidation,
  (newValidation: ValidationMessages | undefined) => {
    validationByLocation.value = {
      [ValidationLocation.METRIC_NAME]: [],
      [ValidationLocation.AGGREGATION_LOOKBACK]: [],
      [ValidationLocation.AGGREGATION_HISTOGRAM_PERCENTILE]: []
    }
    if (newValidation && newValidation.length > 0) {
      newValidation.forEach((message) => {
        const location = message.location[0] as ValidationLocation
        validationByLocation.value[location].push(message.message)
        switch (location) {
          case ValidationLocation.METRIC_NAME:
            metricName.value = (message.replacement_value as MetricBackendCustomQuery).metric_name
            break
          case ValidationLocation.AGGREGATION_LOOKBACK:
            aggregationLookback.value = (
              message.replacement_value as MetricBackendCustomQuery
            ).aggregation_lookback
            break
          case ValidationLocation.AGGREGATION_HISTOGRAM_PERCENTILE:
            aggregationHistogramPercentile.value = (
              message.replacement_value as MetricBackendCustomQuery
            ).aggregation_histogram_percentile
            break
        }
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
          <FormValidation :validation="validationByLocation.metric_name"></FormValidation>
          <FormAutocompleter
            v-model="metricName"
            :autocompleter="metricNameAutocompleter"
            :placeholder="_t('Metric name')"
            :has-error="validationByLocation.metric_name.length > 0"
            @update:model-value="validationByLocation.metric_name = []"
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
          <!-- We can't use the backend-validation from the CmkTimeSpan
            as applying the replacement_value cleans the backend-validation
            effectively causing it to not show the validation messages -->
          <FormValidation :validation="validationByLocation.aggregation_lookback"></FormValidation>
          <CmkTimeSpan
            v-model:data="aggregationLookback"
            :label="''"
            :title="''"
            :input-hint="1"
            :displayed-magnitudes="['hour', 'minute', 'second']"
            :validators="[]"
            :backend-validation="[]"
            @update:data="validationByLocation.aggregation_lookback = []"
          />
          <CmkHelpText :help="AGGREGATION_LOOKBACK_HELP_TEXT" />
          <FormHelp :help="AGGREGATION_LOOKBACK_HELP_TEXT" />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Percentile (histograms)') }}</td>
        <td>
          <CmkInput
            v-model="aggregationHistogramPercentile"
            type="number"
            :unit="'%'"
            :external-errors="validationByLocation.aggregation_histogram_percentile"
            @update:model-value="validationByLocation.aggregation_histogram_percentile = []"
          />
        </td>
      </tr>
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
