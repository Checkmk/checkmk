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
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkList from '@/components/CmkList'

import FormMetricBackendCustomQueryAttribute, {
  type Attribute
} from './FormMetricBackendAttribute.vue'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    metricName?: string | null
    disableValuesOnEmptyKey?: boolean
    strict?: boolean
    staticResourceAttributeKeys?: string[] | null
    indent?: boolean
    orientation?: 'horizontal' | 'vertical'
  }>(),
  {
    metricName: null,
    disableValuesOnEmptyKey: false,
    strict: false,
    staticResourceAttributeKeys: null,
    indent: false,
    orientation: 'horizontal'
  }
)

const valueCellComponent = computed(() => (props.indent ? CmkIndent : 'div'))
const labelCellComponent = computed(() => (props.indent ? 'div' : 'td'))
const valueCellWrapperComponent = computed(() => (props.indent ? 'div' : 'td'))

const resourceAttributes = defineModel<GraphLineQueryAttributes>('resourceAttributes', {
  default: []
})
const scopeAttributes = defineModel<GraphLineQueryAttributes>('scopeAttributes', {
  default: []
})
const dataPointAttributes = defineModel<GraphLineQueryAttributes>('dataPointAttributes', {
  default: []
})

watch(
  () => props.metricName,
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

function clearAttributeSelection() {
  resourceAttribute.value = { key: null, value: null }
  scopeAttribute.value = { key: null, value: null }
  dataPointAttribute.value = { key: null, value: null }
}

defineExpose({ clearAttributeSelection })

// autocompleters
export interface AutoCompleteContext {
  metric_name?: string
  attribute_key?: string
  resource_attributes?: GraphLineQueryAttributes
  scope_attributes?: GraphLineQueryAttributes
  data_point_attributes?: GraphLineQueryAttributes
  static_resource_attribute_keys?: string[]
}

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
      strict: props.strict,
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
  if (props.metricName) {
    context.metric_name = props.metricName
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
  if (props.staticResourceAttributeKeys !== null) {
    context.static_resource_attribute_keys = props.staticResourceAttributeKeys
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
</script>

<template>
  <tr>
    <component
      :is="labelCellComponent"
      class="metric-backend-form-metric-backend-attributes__label-cell"
    >
      {{ _t('Resource attributes') }}
    </component>
    <component :is="valueCellWrapperComponent">
      <component :is="valueCellComponent">
        <CmkList
          :items-props="{ itemData: resourceAttributes }"
          :orientation="props.orientation"
          :try-delete="deleteResourceAttribute"
        >
          <template #item-props="{ index, itemData }">
            <FormMetricBackendCustomQueryAttribute
              :model-value="itemData"
              :autocompleter-getter="
                (key: string | null, isForKey: boolean) =>
                  resourceAttributesAutocompleter(key, isForKey, index)
              "
              :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
              @update:model-value="addResourceAttribute"
            />
          </template>
        </CmkList>
        <FormMetricBackendCustomQueryAttribute
          v-model="resourceAttribute"
          :autocompleter-getter="resourceAttributesAutocompleter"
          :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
          @update:model-value="addResourceAttribute"
        />
      </component>
    </component>
  </tr>
  <tr>
    <component
      :is="labelCellComponent"
      class="metric-backend-form-metric-backend-attributes__label-cell"
    >
      {{ _t('Scope attributes') }}
    </component>
    <component :is="valueCellWrapperComponent">
      <component :is="valueCellComponent">
        <CmkList
          :items-props="{ itemData: scopeAttributes }"
          :orientation="props.orientation"
          :try-delete="deleteScopeAttribute"
        >
          <template #item-props="{ index, itemData }">
            <FormMetricBackendCustomQueryAttribute
              :model-value="itemData"
              :autocompleter-getter="
                (key: string | null, isForKey: boolean) =>
                  scopeAttributesAutocompleter(key, isForKey, index)
              "
              :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
              @update:model-value="addScopeAttribute"
            />
          </template>
        </CmkList>
        <FormMetricBackendCustomQueryAttribute
          v-model="scopeAttribute"
          :autocompleter-getter="scopeAttributesAutocompleter"
          :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
          @update:model-value="addScopeAttribute"
        />
      </component>
    </component>
  </tr>
  <tr>
    <component
      :is="labelCellComponent"
      class="metric-backend-form-metric-backend-attributes__label-cell"
    >
      {{ _t('Data point attributes') }}
    </component>
    <component :is="valueCellWrapperComponent">
      <component :is="valueCellComponent">
        <CmkList
          :items-props="{ itemData: dataPointAttributes }"
          :orientation="props.orientation"
          :try-delete="deleteDataPointAttribute"
        >
          <template #item-props="{ index, itemData }">
            <FormMetricBackendCustomQueryAttribute
              :model-value="itemData"
              :autocompleter-getter="
                (key: string | null, isForKey: boolean) =>
                  dataPointAttributesAutocompleter(key, isForKey, index)
              "
              :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
              @update:model-value="addDataPointAttribute"
            />
          </template>
        </CmkList>
        <FormMetricBackendCustomQueryAttribute
          v-model="dataPointAttribute"
          :autocompleter-getter="dataPointAttributesAutocompleter"
          :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
          @update:model-value="addDataPointAttribute"
        />
      </component>
    </component>
  </tr>
</template>

<style scoped>
.metric-backend-form-metric-backend-attributes__label-cell {
  vertical-align: top;
}
</style>
