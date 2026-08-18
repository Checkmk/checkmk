<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import { type ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/graph_designer'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { computed, ref, watch } from 'vue'

import { type ValidationMessages } from '@/form/private/validation'

import {
  DEFAULT_HISTOGRAM_PERCENTILE,
  DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN,
  buildConsolidationFunction,
  consolidationFunctionFromWire
} from '@/graph-designer/consolidation'
import FormMetricBackendAttributes from '@/metric-backend/FormMetricBackendAttributes.vue'
import FormMetricBackendConsolidation from '@/metric-backend/FormMetricBackendConsolidation.vue'
import FormMetricNameAutocompleter from '@/metric-backend/FormMetricNameAutocompleter.vue'
import { buildAutocompleteContext } from '@/metric-backend/attributeFilterAdapter'
import { useAttributeKeySuggestions } from '@/metric-backend/attributeKeySuggestions'
import { type ConsolidationFunction, outputType } from '@/metric-backend/consolidation/types'
import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import GroupByThenSteps from '@/metric-backend/group-by/GroupByThenSteps.vue'
import {
  type AggregationStep,
  type GroupByInputType,
  type GroupByModel,
  groupByForInputType,
  thenStepsAllowed
} from '@/metric-backend/group-by/types'
import {
  aggregatorFromGroupBy,
  aggregatorToFloatGroupBy,
  aggregatorToThenSteps,
  fractionBelowGroupBy,
  fractionBetweenGroupBy,
  percentileGroupBy
} from '@/metric-backend/group-by/wire'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  attributeFilter?: AttributeFilter
  consolidationFunction: WireConsolidationFunction
  aggregator?: Aggregator
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
// Float grouping rides this sibling; histogram grouping stays embedded in the consolidation.
const aggregator = defineModel<Aggregator | undefined>('aggregator', { default: undefined })

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

const aggregationHistogramThresholdForFractionBelow = computed<number>({
  get: () =>
    consolidation.value.function === 'histogram_fraction_below'
      ? (consolidation.value.threshold ?? DEFAULT_THRESHOLD_FOR_FRACTION_BELOW)
      : DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  set: (value) => {
    if (consolidation.value.function === 'histogram_fraction_below') {
      consolidation.value = { ...consolidation.value, threshold: value }
    }
  }
})

const aggregationHistogramLowerThresholdForFractionBetween = computed<number>({
  get: () =>
    consolidation.value.function === 'histogram_fraction_between'
      ? (consolidation.value.lower_threshold ?? DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN)
      : DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => {
    if (consolidation.value.function === 'histogram_fraction_between') {
      consolidation.value = { ...consolidation.value, lower_threshold: value }
    }
  }
})

const aggregationHistogramUpperThresholdForFractionBetween = computed<number>({
  get: () =>
    consolidation.value.function === 'histogram_fraction_between'
      ? (consolidation.value.upper_threshold ?? DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN)
      : DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => {
    if (consolidation.value.function === 'histogram_fraction_between') {
      consolidation.value = { ...consolidation.value, upper_threshold: value }
    }
  }
})

// The draft the widget edits, not a view of the stored value: an empty pill (a key the
// user has just added but not filled in) is not persisted, so reading the group-by back
// out of the consolidation would drop it again the moment it appears.
const groupBy = ref<GroupByModel>(storedGroupBy())
const thenSteps = ref<AggregationStep[]>(aggregatorToThenSteps(aggregator.value, groupBy.value))

function storedGroupBy(): GroupByModel {
  const stored = consolidation.value
  switch (stored.function) {
    case 'histogram_preserve_fraction_below':
      return fractionBelowGroupBy({
        threshold: stored.threshold ?? 0,
        group_by: stored.group_by
      })
    case 'histogram_preserve_fraction_between':
      return fractionBetweenGroupBy({
        lower_threshold: stored.lower_threshold ?? 0,
        upper_threshold: stored.upper_threshold ?? 0,
        group_by: stored.group_by
      })
    case 'histogram_preserve_quantile':
      return percentileGroupBy(stored)
    default:
      return aggregatorToFloatGroupBy(aggregator.value)
  }
}

function groupByInputTypeOf(consolidationFunction: ConsolidationFunction | null): GroupByInputType {
  return consolidationFunction
    ? outputType(consolidationFunction.type, consolidationFunction.function)
    : 'float'
}

function rebuildConsolidation(consolidationFunction: ConsolidationFunction | null): void {
  const inputType = groupByInputTypeOf(consolidationFunction)
  const group = groupByForInputType(inputType, groupBy.value)
  consolidation.value = buildConsolidationFunction(
    consolidationFunction,
    aggregationLookback.value,
    aggregationHistogramPercentile.value,
    aggregationHistogramThresholdForFractionBelow.value,
    aggregationHistogramLowerThresholdForFractionBetween.value,
    aggregationHistogramUpperThresholdForFractionBetween.value,
    group
  )
  aggregator.value = aggregatorFromGroupBy(group, thenSteps.value)
}

const consolidationFunction = computed<ConsolidationFunction | null>({
  get: () => consolidationFunctionFromWire(consolidation.value),
  set: rebuildConsolidation
})

watch([groupBy, thenSteps], () => rebuildConsolidation(consolidationFunction.value))

const groupByInputType = computed<GroupByInputType>(() =>
  groupByInputTypeOf(consolidationFunction.value)
)

const thenStepsShown = computed(() => thenStepsAllowed(groupByInputType.value, groupBy.value))
// Drop chained steps when the grouping no longer allows them, so they do not resurface later.
watch(thenStepsShown, (shown) => {
  if (!shown && thenSteps.value.length > 0) {
    thenSteps.value = []
  }
})

// The group-by pills pick from the same attribute keys as the where clause.
const {
  querySuggestions: groupByQuerySuggestions,
  resolveAttributeKind: groupByResolveAttributeKind,
  suggestionRevision: groupBySuggestionRevision
} = useAttributeKeySuggestions(() => buildAutocompleteContext([], { metricName: metricName.value }))
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
      <tr>
        <td class="gd-form-metric-backend-custom-query__label-cell">{{ _t('Attributes') }}</td>
        <td>
          <FormMetricBackendAttributes
            v-model:attribute-filter="attributeFilter"
            :label="_t('Attributes')"
            :metric-name="metricName"
          />
        </td>
      </tr>
      <tr>
        <td class="gd-form-metric-backend-custom-query__label-cell">{{ _t('Consolidation') }}</td>
        <td>
          <FormMetricBackendConsolidation
            v-model:aggregation-lookback="aggregationLookback"
            v-model:aggregation-histogram-percentile="aggregationHistogramPercentile"
            v-model:aggregation-histogram-threshold-for-fraction-below="
              aggregationHistogramThresholdForFractionBelow
            "
            v-model:aggregation-histogram-lower-threshold-for-fraction-between="
              aggregationHistogramLowerThresholdForFractionBetween
            "
            v-model:aggregation-histogram-upper-threshold-for-fraction-between="
              aggregationHistogramUpperThresholdForFractionBetween
            "
            v-model:consolidation-function="consolidationFunction"
            :label="_t('Consolidation')"
            :metric-types="metricTypes"
          />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Group by') }}</td>
        <td>
          <FormGroupBy
            v-model="groupBy"
            :input-type="groupByInputType"
            :query-suggestions="groupByQuerySuggestions"
            :suggestion-revision="groupBySuggestionRevision"
            :resolve-attribute-kind="groupByResolveAttributeKind"
          />
        </td>
      </tr>
      <GroupByThenSteps v-if="thenStepsShown" v-model="thenSteps" :group-by-keys="groupBy.keys" />
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

.gd-form-metric-backend-custom-query__label-cell {
  vertical-align: top;
}
</style>
