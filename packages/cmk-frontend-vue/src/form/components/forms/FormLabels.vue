<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { onBeforeUpdate, ref, watch } from 'vue'

import CmkList from '@/components/CmkList'
import { type Suggestion } from '@/components/suggestions'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'
import { inputSizes } from '@/components/user-input/sizes'

import { type ValidationMessages, useValidation } from '@/form/components/utils/validation'
import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import FormLabel from '@/form/private/FormLabel.vue'

import FormLabelsLabel from './FormLabelsLabel.vue'

type StringMapping = Record<string, string>

const stringMappingToArray = (mapping: StringMapping): string[] =>
  Object.entries(mapping).map(([key, value]) => `${key}:${value}`)

const arrayToStringMapping = (array: string[]): StringMapping =>
  array.reduce((acc, curr) => {
    const [key, value] = curr.split(':')
    if (key && value) {
      acc[key] = value
    }
    return acc
  }, {} as StringMapping)

const props = defineProps<{
  spec: FormSpec.Labels
  backendValidation: ValidationMessages
}>()

const data = defineModel<StringMapping>('data', { required: true })
const [validation, value] = useValidation<StringMapping>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const keyValuePairs = ref<string[]>([])
const error = ref<string | null>(null)
const selectedValue = ref<string | null>(null)

const syncDataAndKeyValuePairs = () => {
  const newValues = stringMappingToArray(data.value)
  keyValuePairs.value = newValues
  value.value = arrayToStringMapping(newValues)
}

watch(
  data.value,
  () => {
    syncDataAndKeyValuePairs()
  },
  { immediate: true }
)

watch(keyValuePairs, (newValue) => {
  value.value = arrayToStringMapping(newValue)
})

const validate = (value: string): string | null => {
  const keyValuePair = value.trim().split(':')
  if (keyValuePair.length !== 2 || !keyValuePair[0] || !keyValuePair[1]) {
    error.value = props.spec.i18n.key_value_format_error
    return null
  }
  if (keyValuePairs.value.includes(value)) {
    error.value = props.spec.i18n.uniqueness_error
    return null
  }
  return value.trim()
}

onBeforeUpdate(() => {
  if (error.value) {
    setTimeout(() => {
      error.value = null
    }, 2000)
  }
})

const addItem = (item: string | null) => {
  if (item === null) {
    return
  }
  if (validate(item)) {
    keyValuePairs.value = [...keyValuePairs.value, item]
  }
  selectedValue.value = null
}

function filterKeyValuePairs(element: Suggestion) {
  if (element.name === null) {
    return false
  }
  const key = element.name.split(':')[0]
  if (key === undefined) {
    return true
  }
  return !(key in value.value)
}

const deleteItem = (index: number) => {
  keyValuePairs.value.splice(index, 1)
  value.value = arrayToStringMapping(keyValuePairs.value)
  return true
}
</script>

<template>
  <CmkList
    :items-props="{ itemData: keyValuePairs }"
    orientation="vertical"
    :try-delete="deleteItem"
  >
    <template #item-props="{ itemData }">
      <FormLabel>
        <FormLabelsLabel :label-source="props.spec.label_source" :value="itemData" />
      </FormLabel>
    </template>
  </CmkList>
  <div v-if="!props.spec.max_labels || keyValuePairs.length < props.spec.max_labels">
    <!-- In formLabel, the size on input is a fixed size -->
    <!-- @vue-ignore keydown.enter does not exist on FormAutocompleter -->
    <FormAutocompleter
      v-model="selectedValue"
      :size="inputSizes['MEDIUM'].width"
      :autocompleter="props.spec.autocompleter"
      :placeholder="props.spec.i18n.add_some_labels"
      :filter="filterKeyValuePairs"
      @keydown.enter="
        (e: KeyboardEvent) => {
          const v = (e.target as HTMLInputElement).value
          if (v.length > 0) {
            validate(v)
          }
        }
      "
      @update:model-value="addItem"
    />
  </div>
  <div v-else class="form-labels__error">{{ props.spec.i18n.max_labels_reached }}</div>
  <FormValidation :validation="validation"></FormValidation>
  <div v-if="error" class="form-labels__error">{{ error }}</div>
</template>

<style scoped>
.form-labels__error {
  margin: 0;
  padding: 5px;
  background-color: rgb(247 65 65);
  color: var(--font-color);
  display: block;
  border-radius: 4px;
  box-shadow: none;
}
</style>
