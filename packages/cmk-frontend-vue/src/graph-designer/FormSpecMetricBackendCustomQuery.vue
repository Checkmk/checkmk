<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/graph_designer'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import { type ValidationMessages } from '@/form'
import FormHelp from '@/form/private/FormHelp.vue'

import type { ConsolidationFunction } from '@/metric-backend/consolidation/types'

import FormMetricBackendCustomQuery from './FormMetricBackendCustomQuery.vue'
import { buildConsolidationFunction, consolidationFunctionFromWire } from './consolidation'
import { metricBackendMacroHelp } from './constants'

const { _t } = usei18n()

const props = defineProps<{
  spec: MetricBackendCustomQuery
  backendValidation: ValidationMessages
}>()

const data = defineModel<MetricBackendCustomQuery>('data', { required: true })

const serviceNameTemplateErrors = computed<string[]>(() =>
  props.backendValidation
    .filter((message) => message.location[0] === 'service_name_template')
    .map((message) => message.message)
)

const componentId = useId()

// MetricBackendCustomQuery has no persisted consolidation function, only the two
// numbers below; the picked function is kept here, local to this component instance.
const pickedFunction = ref<ConsolidationFunction | null>(null)

const consolidation = computed<WireConsolidationFunction>({
  get: () =>
    buildConsolidationFunction(
      pickedFunction.value,
      data.value.aggregation_lookback,
      data.value.aggregation_histogram_percentile,
      data.value.aggregation_histogram_threshold_for_fraction_below,
      data.value.aggregation_histogram_lower_threshold_for_fraction_between,
      data.value.aggregation_histogram_upper_threshold_for_fraction_between
    ),
  set: (value) => {
    pickedFunction.value = consolidationFunctionFromWire(value)
    data.value = {
      ...data.value,
      aggregation_lookback: value.lookback_seconds,
      aggregation_histogram_percentile:
        value.function === 'histogram_quantile'
          ? value.percentile
          : data.value.aggregation_histogram_percentile,
      aggregation_histogram_threshold_for_fraction_below:
        value.function === 'histogram_fraction_below'
          ? (value.threshold ?? data.value.aggregation_histogram_threshold_for_fraction_below)
          : data.value.aggregation_histogram_threshold_for_fraction_below,
      aggregation_histogram_lower_threshold_for_fraction_between:
        value.function === 'histogram_fraction_between'
          ? (value.lower_threshold ??
            data.value.aggregation_histogram_lower_threshold_for_fraction_between)
          : data.value.aggregation_histogram_lower_threshold_for_fraction_between,
      aggregation_histogram_upper_threshold_for_fraction_between:
        value.function === 'histogram_fraction_between'
          ? (value.upper_threshold ??
            data.value.aggregation_histogram_upper_threshold_for_fraction_between)
          : data.value.aggregation_histogram_upper_threshold_for_fraction_between
    }
  }
})
</script>

<template>
  <FormMetricBackendCustomQuery
    :id="componentId"
    v-model:metric-name="data.metric_name"
    v-model:attribute-filter="data.attribute_filter"
    v-model:consolidation="consolidation"
    :backend-validation="props.backendValidation"
  >
    <template #additional-rows>
      <tr>
        <td>{{ _t('Service name template') }}</td>
        <td>
          <div class="gd-form-spec-metric-backend-custom-query__service-name-template">
            <CmkInput
              v-model="data.service_name_template"
              type="text"
              field-size="large"
              :placeholder="_t('Service name template')"
              :external-errors="serviceNameTemplateErrors"
            />
            <CmkHelpText :help="metricBackendMacroHelp()" />
          </div>
          <FormHelp :help="metricBackendMacroHelp()" />
        </td>
      </tr>
    </template>
  </FormMetricBackendCustomQuery>
</template>

<style scoped>
.gd-form-spec-metric-backend-custom-query__service-name-template {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
