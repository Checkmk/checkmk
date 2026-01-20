<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  GraphLineQueryAttribute,
  GraphLineQueryAttributes
} from 'cmk-shared-typing/typescript/graph_designer'
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import type { ValidationMessages } from '@/form'

import FormMetricBackendAttributeSection from './FormMetricBackendAttributeSection.vue'

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

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })

enum ValidationLocation {
  RESOURCE_ATTRIBUTES = 'resource_attributes',
  SCOPE_ATTRIBUTES = 'scope_attributes',
  DATA_POINT_ATTRIBUTES = 'data_point_attributes'
}

type ValidationByLocation = {
  [ValidationLocation.RESOURCE_ATTRIBUTES]: string[]
  [ValidationLocation.SCOPE_ATTRIBUTES]: string[]
  [ValidationLocation.DATA_POINT_ATTRIBUTES]: string[]
}

const validationByLocation = ref<ValidationByLocation>({
  [ValidationLocation.RESOURCE_ATTRIBUTES]: [],
  [ValidationLocation.SCOPE_ATTRIBUTES]: [],
  [ValidationLocation.DATA_POINT_ATTRIBUTES]: []
})

const resourceAttributes = defineModel<GraphLineQueryAttributes>('resourceAttributes', {
  default: []
})
const scopeAttributes = defineModel<GraphLineQueryAttributes>('scopeAttributes', {
  default: []
})
const dataPointAttributes = defineModel<GraphLineQueryAttributes>('dataPointAttributes', {
  default: []
})

const resourceSection = ref<InstanceType<typeof FormMetricBackendAttributeSection> | null>(null)
const scopeSection = ref<InstanceType<typeof FormMetricBackendAttributeSection> | null>(null)
const dataPointSection = ref<InstanceType<typeof FormMetricBackendAttributeSection> | null>(null)

immediateWatch(
  () => backendValidation.value,
  (newValidation: ValidationMessages | undefined) => {
    validationByLocation.value = {
      [ValidationLocation.RESOURCE_ATTRIBUTES]: [],
      [ValidationLocation.SCOPE_ATTRIBUTES]: [],
      [ValidationLocation.DATA_POINT_ATTRIBUTES]: []
    }
    if (newValidation && newValidation.length > 0) {
      newValidation.forEach((message) => {
        const location = message.location[0] as ValidationLocation
        validationByLocation.value[location].push(message.message)
        switch (location) {
          case ValidationLocation.RESOURCE_ATTRIBUTES:
            resourceAttributes.value = message.replacement_value as GraphLineQueryAttributes
            break
          case ValidationLocation.SCOPE_ATTRIBUTES:
            scopeAttributes.value = message.replacement_value as GraphLineQueryAttributes
            break
          case ValidationLocation.DATA_POINT_ATTRIBUTES:
            dataPointAttributes.value = message.replacement_value as GraphLineQueryAttributes
            break
        }
      })
    }
  }
)

watch(
  () => props.metricName,
  () => {
    resourceSection.value?.clearAttributeSelection()
    scopeSection.value?.clearAttributeSelection()
    dataPointSection.value?.clearAttributeSelection()
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

function clearAttributeSelection() {
  resourceSection.value?.clearAttributeSelection()
  scopeSection.value?.clearAttributeSelection()
  dataPointSection.value?.clearAttributeSelection()
}

function hasInvalidAttributes(): boolean {
  return (
    resourceAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '') ||
    scopeAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '') ||
    dataPointAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '')
  )
}

function getValidationMessages(): ValidationMessages {
  const messages: ValidationMessages = []

  if (resourceAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '')) {
    messages.push({
      message: 'Resource attribute values cannot be empty.',
      location: ['resource_attributes'],
      replacement_value: resourceAttributes.value
    })
  }

  if (scopeAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '')) {
    messages.push({
      message: 'Scope attribute values cannot be empty.',
      location: ['scope_attributes'],
      replacement_value: scopeAttributes.value
    })
  }

  if (dataPointAttributes.value.some((attr) => attr.value === null || attr.value.trim() === '')) {
    messages.push({
      message: 'Data point attribute values cannot be empty.',
      location: ['data_point_attributes'],
      replacement_value: dataPointAttributes.value
    })
  }

  return messages
}

defineExpose({ clearAttributeSelection, hasInvalidAttributes, getValidationMessages })

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

function getResourceAutoCompleterContext(
  key: string | null = null,
  ignoreExisting: { index: number } | null = null
): AutoCompleteContext {
  return getAutoCompleterContext(
    key,
    ignoreExisting ? { attributeType: AttributeType.RESOURCE, index: ignoreExisting.index } : null
  )
}

function getScopeAutoCompleterContext(
  key: string | null = null,
  ignoreExisting: { index: number } | null = null
): AutoCompleteContext {
  return getAutoCompleterContext(
    key,
    ignoreExisting ? { attributeType: AttributeType.SCOPE, index: ignoreExisting.index } : null
  )
}

function getDataPointAutoCompleterContext(
  key: string | null = null,
  ignoreExisting: { index: number } | null = null
): AutoCompleteContext {
  return getAutoCompleterContext(
    key,
    ignoreExisting ? { attributeType: AttributeType.DATA_POINT, index: ignoreExisting.index } : null
  )
}

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
      (_attribute: GraphLineQueryAttribute, index: number) =>
        _attribute.value !== null &&
        !(
          ignoreExisting &&
          ignoreExisting.attributeType === AttributeType.RESOURCE &&
          ignoreExisting.index === index
        )
    )
  }
  if (scopeAttributes.value.length > 0) {
    context.scope_attributes = scopeAttributes.value.filter(
      (_attribute: GraphLineQueryAttribute, index: number) =>
        _attribute.value !== null &&
        !(
          ignoreExisting &&
          ignoreExisting.attributeType === AttributeType.SCOPE &&
          ignoreExisting.index === index
        )
    )
  }
  if (dataPointAttributes.value.length > 0) {
    context.data_point_attributes = dataPointAttributes.value.filter(
      (_attribute: GraphLineQueryAttribute, index: number) =>
        _attribute.value !== null &&
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
</script>

<template>
  <FormMetricBackendAttributeSection
    ref="resourceSection"
    v-model="resourceAttributes"
    v-model:validation="validationByLocation.resource_attributes"
    :label="_t('Resource attributes')"
    key-ident="monitored_resource_attributes_keys_backend"
    value-ident="monitored_resource_attributes_values_backend"
    :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
    :indent="props.indent"
    :orientation="props.orientation"
    :strict="props.strict"
    :get-auto-completer-context="getResourceAutoCompleterContext"
  />
  <FormMetricBackendAttributeSection
    ref="scopeSection"
    v-model="scopeAttributes"
    v-model:validation="validationByLocation.scope_attributes"
    :label="_t('Scope attributes')"
    key-ident="monitored_scope_attributes_keys_backend"
    value-ident="monitored_scope_attributes_values_backend"
    :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
    :indent="props.indent"
    :orientation="props.orientation"
    :strict="props.strict"
    :get-auto-completer-context="getScopeAutoCompleterContext"
  />
  <FormMetricBackendAttributeSection
    ref="dataPointSection"
    v-model="dataPointAttributes"
    v-model:validation="validationByLocation.data_point_attributes"
    :label="_t('Data point attributes')"
    key-ident="monitored_data_point_attributes_keys_backend"
    value-ident="monitored_data_point_attributes_values_backend"
    :disable-values-on-empty-key="props.disableValuesOnEmptyKey"
    :indent="props.indent"
    :orientation="props.orientation"
    :strict="props.strict"
    :get-auto-completer-context="getDataPointAutoCompleterContext"
  />
</template>
