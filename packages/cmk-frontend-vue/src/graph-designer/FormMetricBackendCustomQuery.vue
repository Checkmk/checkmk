<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type GraphLineQueryAttribute,
  type GraphLineQueryAttributes
} from 'cmk-shared-typing/typescript/graph_designer'
import { type MetricBackendCustomQueryAggregationLookback } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'
import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkList from '@/components/CmkList'
import { type Suggestion } from '@/components/CmkSuggestions'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

import FormMetricBackendCustomQueryAttribute, {
  type Attribute
} from './private/FormMetricBackendCustomQueryAttribute.vue'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  resourceAttributes: GraphLineQueryAttributes
  scopeAttributes: GraphLineQueryAttributes
  dataPointAttributes: GraphLineQueryAttributes
  aggregationLookback: MetricBackendCustomQueryAggregationLookback
  aggregationHistogramPercentile: number
}

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
const aggregationLookback = defineModel<MetricBackendCustomQueryAggregationLookback>(
  'aggregationLookback',
  {
    required: true
  }
)
const aggregationHistogramPercentile = defineModel<number>('aggregationHistogramPercentile', {
  required: true
})

// Clear form fields if one changes

watch(
  () => metricName.value,
  () => {
    resourceAttribute.value = { key: null, value: null }
    scopeAttribute.value = { key: null, value: null }
    dataPointAttribute.value = { key: null, value: null }
    resourceAttributes.value = []
    scopeAttributes.value = []
    dataPointAttributes.value = []
  }
)

watch(
  () => resourceAttributes.value,
  () => {
    scopeAttributes.value = []
    dataPointAttributes.value = []
  }
)

watch(
  () => scopeAttributes.value,
  () => {
    dataPointAttributes.value = []
  }
)

// Some internal vars

const resourceAttribute = ref<Attribute>({
  key: null,
  value: null
})
const scopeAttribute = ref<Attribute>({ key: null, value: null })
const dataPointAttribute = ref<Attribute>({
  key: null,
  value: null
})

// autocompleters
export interface AutoCompleteContext {
  metric_name?: string
  attribute_key?: string
  resource_attributes?: GraphLineQueryAttributes
  scope_attributes?: GraphLineQueryAttributes
  data_point_attributes?: GraphLineQueryAttributes
}

const metricNameAutocompleter = computed<Autocompleter>(() => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_metrics_backend',
    params: {
      strict: true,
      context: getAutoCompleterContext()
    }
  }
}))

enum AttributeType {
  RESOURCE,
  SCOPE,
  DATA_POINT
}

const attributeAutoCompleter = (
  ident: string,
  key: string | null,
  isForKey: boolean,
  ignoreExisting: { attributeType: AttributeType; index: number } | null
): Autocompleter => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident,
    params: {
      strict: true,
      context: getAutoCompleterContext(isForKey ? null : key, ignoreExisting)
    }
  }
})

const resourceAttributesAutocompleter = (
  key: string | null,
  isForKey: boolean,
  ignoreExistingIndex: number | null = null
): Autocompleter => {
  return attributeAutoCompleter(
    isForKey
      ? 'monitored_resource_attributes_keys_backend'
      : 'monitored_resource_attributes_values_backend',
    key,
    isForKey,
    ignoreExistingIndex !== null
      ? { attributeType: AttributeType.RESOURCE, index: ignoreExistingIndex }
      : null
  )
}

const scopeAttributesAutocompleter = (
  key: string | null,
  isForKey: boolean,
  ignoreExistingIndex: number | null = null
): Autocompleter =>
  attributeAutoCompleter(
    isForKey
      ? 'monitored_scope_attributes_keys_backend'
      : 'monitored_scope_attributes_values_backend',
    key,
    isForKey,
    ignoreExistingIndex !== null
      ? { attributeType: AttributeType.SCOPE, index: ignoreExistingIndex }
      : null
  )

const dataPointAttributesAutocompleter = (
  key: string | null,
  isForKey: boolean,
  ignoreExistingIndex: number | null = null
): Autocompleter =>
  attributeAutoCompleter(
    isForKey
      ? 'monitored_data_point_attributes_keys_backend'
      : 'monitored_data_point_attributes_values_backend',
    key,
    isForKey,
    ignoreExistingIndex !== null
      ? { attributeType: AttributeType.DATA_POINT, index: ignoreExistingIndex }
      : null
  )

// actions

function getAutoCompleterContext(
  key: string | null = null,
  ignoreExisting: { attributeType: AttributeType; index: number } | null = null
): AutoCompleteContext {
  const context: AutoCompleteContext = {}
  if (metricName.value) {
    context.metric_name = metricName.value
  }
  if (resourceAttributes.value.length > 0) {
    context.resource_attributes = resourceAttributes.value.filter(
      (attribute: Attribute, index: number) =>
        attribute.value !== null &&
        !(
          ignoreExisting &&
          ignoreExisting.attributeType === AttributeType.RESOURCE &&
          ignoreExisting.index === index
        )
    )
  }
  if (scopeAttributes.value.length > 0) {
    context.scope_attributes = scopeAttributes.value.filter(
      (attribute: Attribute, index: number) =>
        attribute.value !== null &&
        !(
          ignoreExisting &&
          ignoreExisting.attributeType === AttributeType.SCOPE &&
          ignoreExisting.index === index
        )
    )
  }
  if (dataPointAttributes.value.length > 0) {
    context.data_point_attributes = dataPointAttributes.value.filter(
      (attribute: Attribute, index: number) =>
        attribute.value !== null &&
        !(
          ignoreExisting &&
          ignoreExisting.attributeType === AttributeType.DATA_POINT &&
          ignoreExisting.index === index
        )
    )
  }
  if (key !== '' && key !== null) {
    context.attribute_key = key
  }
  return context
}

function addResourceAttribute() {
  if (
    resourceAttribute.value.key !== '' &&
    resourceAttribute.value.key !== null &&
    resourceAttribute.value.value !== '' &&
    resourceAttribute.value.value !== null
  ) {
    resourceAttributes.value.push(resourceAttribute.value as GraphLineQueryAttribute)
    resourceAttribute.value = { key: null, value: null }
  }
}

function deleteResourceAttribute(index: number) {
  resourceAttributes.value.splice(index, 1)
  resourceAttribute.value = { key: null, value: null }
  return true
}

function addScopeAttribute() {
  if (
    scopeAttribute.value.key !== '' &&
    scopeAttribute.value.key !== null &&
    scopeAttribute.value.value !== '' &&
    scopeAttribute.value.value !== null
  ) {
    scopeAttributes.value.push(scopeAttribute.value as GraphLineQueryAttribute)
    scopeAttribute.value = { key: null, value: null }
  }
}

function deleteScopeAttribute(index: number) {
  scopeAttributes.value.splice(index, 1)
  scopeAttribute.value = { key: null, value: null }
  return true
}

function addDataPointAttribute() {
  if (
    dataPointAttribute.value.key !== '' &&
    dataPointAttribute.value.key !== null &&
    dataPointAttribute.value.value !== '' &&
    dataPointAttribute.value.value !== null
  ) {
    dataPointAttributes.value.push(dataPointAttribute.value as GraphLineQueryAttribute)
    dataPointAttribute.value = { key: null, value: null }
  }
}

function deleteDataPointAttribute(index: number) {
  dataPointAttributes.value.splice(index, 1)
  dataPointAttribute.value = { key: null, value: null }
  return true
}

// Unit for interval/time frame of aggregation sum rate

const aggregationLookbackUnitSuggestions: Suggestion[] = [
  { name: 's', title: untranslated('s') },
  { name: 'min', title: untranslated('min') }
]
</script>

<template>
  <table>
    <tbody>
      <tr>
        <td>{{ _t('Metric') }}</td>
        <td>
          <FormAutocompleter
            v-model="metricName"
            :autocompleter="metricNameAutocompleter"
            :placeholder="_t('Metric name')"
          />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Resource attributes') }}</td>
        <td>
          <CmkList
            :items-props="{ itemData: resourceAttributes }"
            orientation="horizontal"
            :try-delete="deleteResourceAttribute"
          >
            <template #item-props="{ index, itemData }">
              <FormMetricBackendCustomQueryAttribute
                :model-value="itemData"
                :autocompleter-getter="
                  (key: string | null, isForKey: boolean) =>
                    resourceAttributesAutocompleter(key, isForKey, index)
                "
                @update:model-value="addResourceAttribute"
              />
            </template>
          </CmkList>
          <FormMetricBackendCustomQueryAttribute
            v-model="resourceAttribute"
            :autocompleter-getter="resourceAttributesAutocompleter"
            @update:model-value="addResourceAttribute"
          />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Scope attributes') }}</td>
        <td>
          <CmkList
            :items-props="{ itemData: scopeAttributes }"
            orientation="horizontal"
            :try-delete="deleteScopeAttribute"
          >
            <template #item-props="{ index, itemData }">
              <FormMetricBackendCustomQueryAttribute
                :model-value="itemData"
                :autocompleter-getter="
                  (key: string | null, isForKey: boolean) =>
                    scopeAttributesAutocompleter(key, isForKey, index)
                "
                @update:model-value="addScopeAttribute"
              />
            </template>
          </CmkList>
          <FormMetricBackendCustomQueryAttribute
            v-model="scopeAttribute"
            :autocompleter-getter="scopeAttributesAutocompleter"
            @update:model-value="addScopeAttribute"
          />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Data point attributes') }}</td>
        <td>
          <CmkList
            :items-props="{ itemData: dataPointAttributes }"
            orientation="horizontal"
            :try-delete="deleteDataPointAttribute"
          >
            <template #item-props="{ index, itemData }">
              <FormMetricBackendCustomQueryAttribute
                :model-value="itemData"
                :autocompleter-getter="
                  (key: string | null, isForKey: boolean) =>
                    dataPointAttributesAutocompleter(key, isForKey, index)
                "
                @update:model-value="addDataPointAttribute"
              />
            </template>
          </CmkList>
          <FormMetricBackendCustomQueryAttribute
            v-model="dataPointAttribute"
            :autocompleter-getter="dataPointAttributesAutocompleter"
            @update:model-value="addDataPointAttribute"
          />
        </td>
      </tr>
      <tr>
        <td>{{ _t('Aggregation lookback') }}</td>
        <td>
          <div>
            <CmkInput v-model="aggregationLookback.value" type="number" />
          </div>
          <div>
            <CmkDropdown
              v-model:selected-option="aggregationLookback.unit"
              :options="{ type: 'fixed', suggestions: aggregationLookbackUnitSuggestions }"
              :label="_t('Time range')"
            />
          </div>
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

div {
  display: inline-block;
  margin-right: 1px;
}
</style>
