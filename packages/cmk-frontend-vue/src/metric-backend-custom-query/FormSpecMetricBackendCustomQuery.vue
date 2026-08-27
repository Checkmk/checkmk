<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import { type ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { staticAssertNever } from 'cmk-ui-library/lib/typeUtils'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref, watch } from 'vue'

import { type ValidationMessages } from '@/form'
import FormHelp from '@/form/private/FormHelp.vue'

import SourceFormStack from '@/graphing/designer/components/forms/SourceFormStack.vue'
import SourceFormText from '@/graphing/designer/components/forms/SourceFormText.vue'

import FormMetricBackendCustomQuery from './FormMetricBackendCustomQuery.vue'
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

function storedConsolidation(stored: MetricBackendCustomQuery): WireConsolidationFunction {
  const fn = stored.consolidation_function
  const lookbackSeconds = stored.aggregation_lookback
  switch (fn) {
    case 'gauge_last':
    case 'gauge_max':
    case 'gauge_avg':
    case 'gauge_min':
      return { type: 'gauge', function: fn, lookback_seconds: lookbackSeconds }
    case 'sum_rate':
    case 'sum_last_raw':
    case 'sum_delta':
      return { type: 'sum', function: fn, lookback_seconds: lookbackSeconds }
    case 'histogram_count_delta':
    case 'histogram_count_rate':
    case 'histogram_sum_rate':
    case 'histogram_sum_delta':
    case 'histogram_sum_raw':
      return { type: 'histogram', function: fn, lookback_seconds: lookbackSeconds }
    case 'histogram_quantile':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        percentile: stored.aggregation_histogram_percentile
      }
    case 'histogram_fraction_below':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        threshold: stored.aggregation_histogram_threshold_for_fraction_below
      }
    case 'histogram_fraction_between':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        lower_threshold: stored.aggregation_histogram_lower_threshold_for_fraction_between,
        upper_threshold: stored.aggregation_histogram_upper_threshold_for_fraction_between
      }
    case 'histogram_preserve_quantile':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        percentile: stored.aggregation_histogram_percentile,
        group_by: stored.aggregation_histogram_group_by
      }
    case 'histogram_preserve_fraction_below':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        threshold: stored.aggregation_histogram_threshold_for_fraction_below,
        group_by: stored.aggregation_histogram_group_by
      }
    case 'histogram_preserve_fraction_between':
      return {
        type: 'histogram',
        function: fn,
        lookback_seconds: lookbackSeconds,
        lower_threshold: stored.aggregation_histogram_lower_threshold_for_fraction_between,
        upper_threshold: stored.aggregation_histogram_upper_threshold_for_fraction_between,
        group_by: stored.aggregation_histogram_group_by
      }
    default:
      staticAssertNever(fn)
      throw new Error(`unhandled consolidation function: ${JSON.stringify(fn)}`)
  }
}

// A bound defineModel reflects a write only after the parent's prop flows back (next
// flush), so same-tick writes (e.g. consolidation + aggregator on one picker change)
// would each spread a stale data.value. This mirror gives them a synchronous view.
const local = ref<MetricBackendCustomQuery>({ ...data.value })

watch(data, (incoming) => {
  if (incoming !== local.value) {
    local.value = { ...incoming }
  }
})

function commit(next: MetricBackendCustomQuery): void {
  local.value = next
  data.value = next
}

function update(patch: Partial<MetricBackendCustomQuery>): void {
  commit({ ...local.value, ...patch })
}

const metricName = computed<string | null>({
  get: () => local.value.metric_name,
  set: (value) => update({ metric_name: value })
})

const attributeFilter = computed<AttributeFilter | undefined>({
  get: () => local.value.attribute_filter,
  set: (value) => {
    const { attribute_filter: _dropped, ...rest } = local.value
    commit(value === undefined ? rest : { ...rest, attribute_filter: value })
  }
})

const serviceNameTemplate = computed<string>({
  get: () => local.value.service_name_template,
  set: (value) => update({ service_name_template: value })
})

const consolidation = computed<WireConsolidationFunction>({
  get: () => storedConsolidation(local.value),
  set: (value) => {
    const current = local.value
    update({
      consolidation_function: value.function,
      aggregation_lookback: value.lookback_seconds,
      aggregation_histogram_percentile:
        value.function === 'histogram_quantile' || value.function === 'histogram_preserve_quantile'
          ? value.percentile
          : current.aggregation_histogram_percentile,
      aggregation_histogram_threshold_for_fraction_below:
        value.function === 'histogram_fraction_below' ||
        value.function === 'histogram_preserve_fraction_below'
          ? value.threshold
          : current.aggregation_histogram_threshold_for_fraction_below,
      aggregation_histogram_lower_threshold_for_fraction_between:
        value.function === 'histogram_fraction_between' ||
        value.function === 'histogram_preserve_fraction_between'
          ? value.lower_threshold
          : current.aggregation_histogram_lower_threshold_for_fraction_between,
      aggregation_histogram_upper_threshold_for_fraction_between:
        value.function === 'histogram_fraction_between' ||
        value.function === 'histogram_preserve_fraction_between'
          ? value.upper_threshold
          : current.aggregation_histogram_upper_threshold_for_fraction_between,
      aggregation_histogram_group_by:
        value.function === 'histogram_preserve_quantile' ||
        value.function === 'histogram_preserve_fraction_below' ||
        value.function === 'histogram_preserve_fraction_between'
          ? value.group_by
          : []
    })
  }
})

// Scalar grouping rides the aggregator sibling; stored as-is, null when ungrouped.
const aggregator = computed<Aggregator | undefined>({
  get: () => local.value.aggregator ?? undefined,
  set: (value) => {
    update({ aggregator: value ?? null })
  }
})
</script>

<template>
  <FormMetricBackendCustomQuery
    :id="componentId"
    v-model:metric-name="metricName"
    v-model:attribute-filter="attributeFilter"
    v-model:consolidation="consolidation"
    v-model:aggregator="aggregator"
    :backend-validation="props.backendValidation"
  >
    <template #additional-fields>
      <SourceFormStack spacing="label">
        <SourceFormText variant="description">{{ _t('Service name template') }}</SourceFormText>
        <div class="mbcq-form-spec-metric-backend-custom-query__service-name-template">
          <CmkInput
            v-model="serviceNameTemplate"
            type="text"
            field-size="large"
            :placeholder="_t('Service name template')"
            :external-errors="serviceNameTemplateErrors"
          />
          <CmkHelpText :help="metricBackendMacroHelp()" />
        </div>
        <FormHelp :help="metricBackendMacroHelp()" />
      </SourceFormStack>
    </template>
  </FormMetricBackendCustomQuery>
</template>

<style scoped>
.mbcq-form-spec-metric-backend-custom-query__service-name-template {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
