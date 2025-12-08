<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  type GraphLineQueryAttribute,
  type GraphLineQueryAttributes,
  type QueryAggregationSumRate
} from 'cmk-shared-typing/typescript/graph_designer'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'
import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkList from '@/components/CmkList'
import { type Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FormAutocompleter from '@/form/private/FormAutocompleter/FormAutocompleter.vue'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  resourceAttributes: GraphLineQueryAttributes
  scopeAttributes: GraphLineQueryAttributes
  dataPointAttributes: GraphLineQueryAttributes
  aggregationSum: QueryAggregationSumRate | null
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
const aggregationSum = defineModel<QueryAggregationSumRate | null>('aggregationSum', {
  default: null
})
const aggregationHistogramPercentile = defineModel<number>('aggregationHistogramPercentile', {
  required: true
})

// Clear form fields if one changes

watch(
  () => metricName.value,
  () => {
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

const resourceAttribute = ref<{ key: string | null; value: string | null }>({
  key: null,
  value: null
})
const scopeAttribute = ref<{ key: string | null; value: string | null }>({ key: null, value: null })
const dataPointAttribute = ref<{ key: string | null; value: string | null }>({
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

const resourceAttributesAutocompleter = (key: boolean = true): Autocompleter => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: key
      ? 'monitored_resource_attributes_keys_backend'
      : 'monitored_resource_attributes_values_backend',
    params: {
      strict: true,
      context: getAutoCompleterContext(resourceAttribute.value.key)
    }
  }
})

const scopeAttributesAutocompleter = (key: boolean = true): Autocompleter => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: key
      ? 'monitored_scope_attributes_keys_backend'
      : 'monitored_scope_attributes_values_backend',
    params: {
      strict: true,
      context: getAutoCompleterContext(scopeAttribute.value.key)
    }
  }
})

const dataPointAttributesAutocompleter = (key: boolean = true): Autocompleter => ({
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: key
      ? 'monitored_data_point_attributes_keys_backend'
      : 'monitored_data_point_attributes_values_backend',
    params: {
      strict: true,
      context: getAutoCompleterContext(dataPointAttribute.value.key)
    }
  }
})

// actions

function getAutoCompleterContext(key: string | null = null) {
  const context: AutoCompleteContext = {}
  if (metricName.value) {
    context.metric_name = metricName.value
  }
  if (resourceAttributes.value.length > 0) {
    context.resource_attributes = resourceAttributes.value
  }
  if (scopeAttributes.value.length > 0) {
    context.scope_attributes = scopeAttributes.value
  }
  if (dataPointAttributes.value.length > 0) {
    context.data_point_attributes = dataPointAttributes.value
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

const aggregationSumRateUnitSuggestions: Suggestion[] = [
  { name: 's', title: untranslated('s') },
  { name: 'min', title: untranslated('min') },
  { name: 'h', title: untranslated('h') }
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
            <template #item-props="{ itemData }">
              {{ itemData.key }}{{ itemData.value ? `:${itemData.value}` : '' }}
            </template>
          </CmkList>
          <div>
            <FormAutocompleter
              v-model="resourceAttribute.key"
              :autocompleter="resourceAttributesAutocompleter()"
              :placeholder="_t('Attribute key')"
              @update:model-value="addResourceAttribute"
            />
          </div>
          <div>
            <FormAutocompleter
              v-model="resourceAttribute.value"
              :autocompleter="resourceAttributesAutocompleter(false)"
              :placeholder="_t('Attribute value')"
              @update:model-value="addResourceAttribute"
            />
          </div>
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
            <template #item-props="{ itemData }">
              {{ itemData.key }}{{ itemData.value ? `:${itemData.value}` : '' }}
            </template>
          </CmkList>
          <div>
            <FormAutocompleter
              v-model="scopeAttribute.key"
              :autocompleter="scopeAttributesAutocompleter()"
              :placeholder="_t('Attribute key')"
              @update:model-value="addScopeAttribute"
            />
          </div>
          <div>
            <FormAutocompleter
              v-model="scopeAttribute.value"
              :autocompleter="scopeAttributesAutocompleter(false)"
              :placeholder="_t('Attribute value')"
              @update:model-value="addScopeAttribute"
            />
          </div>
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
            <template #item-props="{ itemData }">
              {{ itemData.key }}{{ itemData.value ? `:${itemData.value}` : '' }}
            </template>
          </CmkList>
          <div>
            <FormAutocompleter
              v-model="dataPointAttribute.key"
              :autocompleter="dataPointAttributesAutocompleter()"
              :placeholder="_t('Attribute key')"
              @update:model-value="addDataPointAttribute"
            />
          </div>
          <div>
            <FormAutocompleter
              v-model="dataPointAttribute.value"
              :autocompleter="dataPointAttributesAutocompleter(false)"
              :placeholder="_t('Attribute value')"
              @update:model-value="addDataPointAttribute"
            />
          </div>
        </td>
      </tr>
      <tr v-if="aggregationSum !== null && aggregationSum.type === 'rate'">
        <td>
          <CmkCheckbox v-model="aggregationSum.enabled" :label="_t('Apply rate (sums)')" />
        </td>
        <td>
          <CmkInput v-model="aggregationSum.value" type="number" />
          <CmkDropdown
            v-model:selected-option="aggregationSum.unit"
            :options="{ type: 'fixed', suggestions: aggregationSumRateUnitSuggestions }"
            :label="_t('Time range')"
          />
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
