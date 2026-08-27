<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, ref, watch } from 'vue'

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
  groupFractionBelowThresholdToWire,
  groupFractionLowerThresholdToWire,
  groupFractionUpperThresholdToWire,
  groupKeysToWire,
  groupPercentileToWire,
  percentileGroupBy
} from '@/metric-backend/group-by/wire'
import {
  DEFAULT_HISTOGRAM_PERCENTILE,
  DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN
} from '@/metric-backend/histogram-params'

import type { GraphItemsStore } from '../../composables/useGraphItems'
import type { DraftMetricBackendItem } from '../../drafts'
import type { MetricBackendItem } from '../../types'
import SourceFormField from './SourceFormField.vue'
import SourceFormStack from './SourceFormStack.vue'
import SourceFormText from './SourceFormText.vue'

const { item, store, metricNameErrors, consolidationErrors } = defineProps<{
  item: DraftMetricBackendItem
  store: GraphItemsStore
  metricNameErrors: TranslatedString[]
  consolidationErrors: TranslatedString[]
}>()

const { _t } = usei18n()

type Consolidation = MetricBackendItem['consolidation_function']

// The picker edits function, lookback and percentile independently and speaks the grouped
// {type, function} shape, while the item stores the flat engine union — so map between them
// (rebuilding the whole value, never spreading, which would decorrelate the union).
function toStored(
  consolidationFunction: ConsolidationFunction,
  lookbackSeconds: number,
  percentile: number,
  thresholdForFractionBelow: number,
  lowerThresholdForFractionBetween: number,
  upperThresholdForFractionBetween: number,
  groupBy: GroupByModel
): Consolidation {
  switch (consolidationFunction?.function) {
    case 'histogram_preserve':
      // "Preserve histograms" is only half a wire function: the group-by clause it is
      // paired with names the other half and owns that half's parameters.
      switch (groupBy.function) {
        case 'percentile':
          return {
            type: 'histogram_preserve_quantile',
            lookback_seconds: lookbackSeconds,
            percentile: groupPercentileToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        case 'fraction_below':
          return {
            type: 'histogram_preserve_fraction_below',
            lookback_seconds: lookbackSeconds,
            threshold: groupFractionBelowThresholdToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        case 'fraction_between':
          return {
            type: 'histogram_preserve_fraction_between',
            lookback_seconds: lookbackSeconds,
            lower_threshold: groupFractionLowerThresholdToWire(groupBy),
            upper_threshold: groupFractionUpperThresholdToWire(groupBy),
            group_by: groupKeysToWire(groupBy.keys)
          }
        default:
          throw new Error(`grouping without a "preserve histograms" pairing: ${groupBy.function}`)
      }
    case 'gauge_max':
      return { type: 'gauge_max', lookback_seconds: lookbackSeconds }
    case 'gauge_avg':
      return { type: 'gauge_avg', lookback_seconds: lookbackSeconds }
    case 'gauge_min':
      return { type: 'gauge_min', lookback_seconds: lookbackSeconds }
    case 'sum_rate':
      return { type: 'sum_rate', lookback_seconds: lookbackSeconds }
    case 'sum_last_raw':
      return { type: 'sum_last_raw', lookback_seconds: lookbackSeconds }
    case 'sum_delta':
      return { type: 'sum_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_quantile':
      return { type: 'histogram_quantile', lookback_seconds: lookbackSeconds, percentile }
    case 'histogram_fraction_below':
      return {
        type: 'histogram_fraction_below',
        lookback_seconds: lookbackSeconds,
        threshold: thresholdForFractionBelow
      }
    case 'histogram_fraction_between':
      return {
        type: 'histogram_fraction_between',
        lookback_seconds: lookbackSeconds,
        lower_threshold: lowerThresholdForFractionBetween,
        upper_threshold: upperThresholdForFractionBetween
      }
    case 'histogram_count_delta':
      return { type: 'histogram_count_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_count_rate':
      return { type: 'histogram_count_rate', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_rate':
      return { type: 'histogram_sum_rate', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_delta':
      return { type: 'histogram_sum_delta', lookback_seconds: lookbackSeconds }
    case 'histogram_sum_raw':
      return { type: 'histogram_sum_raw', lookback_seconds: lookbackSeconds }
    case 'gauge_last':
    default:
      return { type: 'gauge_last', lookback_seconds: lookbackSeconds }
  }
}

function toPicker(consolidation: Consolidation): ConsolidationFunction {
  switch (consolidation.type) {
    case 'gauge_last':
    case 'gauge_max':
    case 'gauge_avg':
    case 'gauge_min':
      return { type: 'gauge', function: consolidation.type }
    case 'sum_rate':
    case 'sum_last_raw':
    case 'sum_delta':
      return { type: 'sum', function: consolidation.type }
    case 'histogram_quantile':
    case 'histogram_count_delta':
    case 'histogram_count_rate':
    case 'histogram_sum_rate':
    case 'histogram_sum_delta':
    case 'histogram_sum_raw':
    case 'histogram_fraction_below':
    case 'histogram_fraction_between':
      return { type: 'histogram', function: consolidation.type }
    case 'histogram_preserve_quantile':
    case 'histogram_preserve_fraction_below':
    case 'histogram_preserve_fraction_between':
      return { type: 'histogram', function: 'histogram_preserve' }
  }
}

function persist(consolidation: Consolidation, aggregator: Aggregator | undefined): void {
  const { aggregator: _dropped, ...rest } = { ...item, consolidation_function: consolidation }
  store.replace(aggregator === undefined ? rest : { ...rest, aggregator })
}

const metricTypes = ref<string[]>([])

const metricName = computed<string | null>({
  get: () => item.metric_name,
  set: (value) => store.replace({ ...item, metric_name: value })
})

const attributeFilter = computed<AttributeFilter | undefined>({
  get: () => item.attribute_filter,
  set: (value) =>
    store.replace({ ...item, attribute_filter: value ?? { type: 'and', conjuncts: [] } })
})

function storeCurrentWith(overrides: {
  lookbackSeconds?: number
  percentile?: number
  thresholdForFractionBelow?: number
  lowerThresholdForFractionBetween?: number
  upperThresholdForFractionBetween?: number
  consolidationFunction?: ConsolidationFunction
}): void {
  const consolidation = overrides.consolidationFunction ?? consolidationFunction.value
  const inputType = outputType(consolidation.type, consolidation.function)
  const group = groupByForInputType(inputType, groupBy.value)
  const stored = toStored(
    consolidation,
    overrides.lookbackSeconds ?? aggregationLookback.value,
    overrides.percentile ?? aggregationHistogramPercentile.value,
    overrides.thresholdForFractionBelow ?? aggregationHistogramThresholdForFractionBelow.value,
    overrides.lowerThresholdForFractionBetween ??
      aggregationHistogramLowerThresholdForFractionBetween.value,
    overrides.upperThresholdForFractionBetween ??
      aggregationHistogramUpperThresholdForFractionBetween.value,
    group
  )
  persist(stored, aggregatorFromGroupBy(group, thenSteps.value))
}

const aggregationLookback = computed<number>({
  get: () => item.consolidation_function.lookback_seconds,
  set: (value) => storeCurrentWith({ lookbackSeconds: value })
})

const aggregationHistogramPercentile = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_quantile'
      ? item.consolidation_function.percentile
      : DEFAULT_HISTOGRAM_PERCENTILE,
  set: (value) => storeCurrentWith({ percentile: value })
})

const aggregationHistogramThresholdForFractionBelow = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_below'
      ? item.consolidation_function.threshold
      : DEFAULT_THRESHOLD_FOR_FRACTION_BELOW,
  set: (value) => storeCurrentWith({ thresholdForFractionBelow: value })
})

const aggregationHistogramLowerThresholdForFractionBetween = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_between'
      ? item.consolidation_function.lower_threshold
      : DEFAULT_LOWER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => storeCurrentWith({ lowerThresholdForFractionBetween: value })
})

const aggregationHistogramUpperThresholdForFractionBetween = computed<number>({
  get: () =>
    item.consolidation_function.type === 'histogram_fraction_between'
      ? item.consolidation_function.upper_threshold
      : DEFAULT_UPPER_THRESHOLD_FOR_FRACTION_BETWEEN,
  set: (value) => storeCurrentWith({ upperThresholdForFractionBetween: value })
})

const consolidationFunction = computed<ConsolidationFunction>({
  get: () => toPicker(item.consolidation_function),
  set: (value) => storeCurrentWith({ consolidationFunction: value })
})

const groupByInputType = computed<GroupByInputType>(() =>
  outputType(consolidationFunction.value.type, consolidationFunction.value.function)
)

// The draft the widget edits, not a view of the stored value: an empty pill (a key the
// user has just added but not filled in) is not persisted, so reading the group-by back
// out of the store would drop it again the moment it appears.
const groupBy = ref<GroupByModel>(storedGroupBy())
const thenSteps = ref<AggregationStep[]>(aggregatorToThenSteps(item.aggregator, groupBy.value))

const thenStepsShown = computed(() => thenStepsAllowed(groupByInputType.value, groupBy.value))
// Drop chained steps when the grouping no longer allows them, so they do not resurface later.
watch(thenStepsShown, (shown) => {
  if (!shown && thenSteps.value.length > 0) {
    thenSteps.value = []
  }
})

function storedGroupBy(): GroupByModel {
  const stored = item.consolidation_function
  switch (stored.type) {
    case 'histogram_preserve_fraction_below':
      return fractionBelowGroupBy(stored)
    case 'histogram_preserve_fraction_between':
      return fractionBetweenGroupBy(stored)
    case 'histogram_preserve_quantile':
      return percentileGroupBy(stored)
    default:
      return aggregatorToFloatGroupBy(item.aggregator)
  }
}

watch([groupBy, thenSteps], () => storeCurrentWith({}))

// The group-by pills pick from the same attribute keys as the where clause.
const {
  querySuggestions: groupByQuerySuggestions,
  resolveAttributeKind: groupByResolveAttributeKind,
  suggestionRevision: groupBySuggestionRevision
} = useAttributeKeySuggestions(() => buildAutocompleteContext([], { metricName: metricName.value }))
</script>

<template>
  <SourceFormStack spacing="label">
    <SourceFormText variant="description">{{ _t('Show') }}</SourceFormText>

    <SourceFormStack spacing="field">
      <SourceFormField
        v-slot="{ controlId, describedBy, invalid }"
        :label="_t('Metric')"
        label-variant="name"
        required
        :errors="metricNameErrors"
      >
        <FormMetricNameAutocompleter
          v-model:metric-name="metricName"
          v-model:metric-types="metricTypes"
          :component-id="controlId"
          :placeholder="_t('Metric name')"
          :label="_t('Metric name')"
          :has-error="invalid"
          :described-by="describedBy"
        />
      </SourceFormField>

      <SourceFormStack spacing="label">
        <SourceFormText variant="description">{{ _t('Where') }}</SourceFormText>
        <FormMetricBackendAttributes
          v-model:attribute-filter="attributeFilter"
          :label="_t('Where: attribute filter')"
          :metric-name="metricName"
        />
      </SourceFormStack>

      <SourceFormStack spacing="label">
        <SourceFormText variant="description">{{ _t('Then consolidate by') }}</SourceFormText>
        <CmkInlineValidation
          v-if="consolidationErrors.length > 0"
          :validation="consolidationErrors"
        />
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
          :label="_t('Then consolidate by: consolidation function and lookback')"
          :metric-types="metricTypes"
          :metric-name="metricName"
        />
      </SourceFormStack>

      <SourceFormStack spacing="label">
        <SourceFormText variant="description">{{ _t('And group by') }}</SourceFormText>
        <FormGroupBy
          v-model="groupBy"
          :input-type="groupByInputType"
          :query-suggestions="groupByQuerySuggestions"
          :suggestion-revision="groupBySuggestionRevision"
          :resolve-attribute-kind="groupByResolveAttributeKind"
          :aria-label="_t('And group by: grouping function and keys')"
        />
        <GroupByThenSteps v-if="thenStepsShown" v-model="thenSteps" :group-by-keys="groupBy.keys" />
      </SourceFormStack>
    </SourceFormStack>
  </SourceFormStack>
</template>
