<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkList from '@/components/CmkList'
import { inputSizes } from '@/components/user-input/sizes'

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'

const { _t } = usei18n()

export interface Query {
  metricName: string | null
  resourceAttributes: string[]
  scopeAttributes: string[]
  dataPointAttributes: string[]
}

const metricName = defineModel<string | null>('metricName', { default: null })
const resourceAttributes = defineModel<string[]>('resourceAttributes', {
  default: []
})
const scopeAttributes = defineModel<string[]>('scopeAttributes', {
  default: []
})
const dataPointAttributes = defineModel<string[]>('dataPointAttributes', {
  default: []
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

const resourceAttribute = ref<string | null>(null)
const scopeAttribute = ref<string | null>(null)
const dataPointAttribute = ref<string | null>(null)

// autocompleters

const metricNameAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_metrics_backend',
    params: { strict: true }
  }
}

const resourceAttributesAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_resource_attributes_backend',
    params: {
      strict: true,
      context: {
        metric: { metric: metricName.value }
      }
    }
  }
}

const scopeAttributesAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_scope_attributes_backend',
    params: {
      strict: true,
      context: {
        metric: { metric: metricName.value },
        resource_attribute: { resource_attribute: resourceAttribute.value }
      }
    }
  }
}

const dataPointAttributesAutocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: {
    ident: 'monitored_data_point_attributes_backend',
    params: {
      strict: true,
      context: {
        metric: { metric: metricName.value },
        resource_attribute: { resource_attribute: resourceAttribute.value },
        scope_attribute: { scope_attribute: scopeAttribute.value }
      }
    }
  }
}

// actions

function addResourceAttribute() {
  if (resourceAttribute.value !== '' && resourceAttribute.value !== null) {
    resourceAttributes.value.push(resourceAttribute.value)
    resourceAttribute.value = null
  }
}

function deleteResourceAttribute(index: number) {
  resourceAttributes.value.splice(index, 1)
  return true
}

function addScopeAttribute() {
  if (scopeAttribute.value !== '' && scopeAttribute.value !== null) {
    scopeAttributes.value.push(scopeAttribute.value)
    scopeAttribute.value = null
  }
}

function deleteScopeAttribute(index: number) {
  scopeAttributes.value.splice(index, 1)
  return true
}

function addDataPointAttribute() {
  if (dataPointAttribute.value !== '' && dataPointAttribute.value !== null) {
    dataPointAttributes.value.push(dataPointAttribute.value)
    dataPointAttribute.value = null
  }
}

function deleteDataPointAttribute(index: number) {
  dataPointAttributes.value.splice(index, 1)
  return true
}
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
            :size="inputSizes['MEDIUM'].width"
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
            <template #item-props="{ itemData }">{{ itemData }}</template>
          </CmkList>
          <FormAutocompleter
            v-model="resourceAttribute"
            :autocompleter="resourceAttributesAutocompleter"
            :size="inputSizes['MEDIUM'].width"
            :placeholder="_t('Attributes')"
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
            <template #item-props="{ itemData }">{{ itemData }}</template>
          </CmkList>
          <FormAutocompleter
            v-model="scopeAttribute"
            :autocompleter="scopeAttributesAutocompleter"
            :size="inputSizes['MEDIUM'].width"
            :placeholder="_t('Attributes')"
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
            <template #item-props="{ itemData }">{{ itemData }}</template>
          </CmkList>
          <FormAutocompleter
            v-model="dataPointAttribute"
            :autocompleter="dataPointAttributesAutocompleter"
            :size="inputSizes['MEDIUM'].width"
            :placeholder="_t('Attributes')"
            @update:model-value="addDataPointAttribute"
          />
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
