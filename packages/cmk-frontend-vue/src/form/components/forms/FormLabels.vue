<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { X } from 'lucide-vue-next'
import { onBeforeUpdate, ref, watch } from 'vue'
import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import { inputSizes } from '../utils/sizes'

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

const addItem = (item: string) => {
  if (validate(item)) {
    keyValuePairs.value = [...keyValuePairs.value, item]
  }
}

const editItem = (editedItem: string, index: number) => {
  if (validate(editedItem)) {
    keyValuePairs.value = [
      ...keyValuePairs.value.slice(0, index),
      editedItem,
      ...keyValuePairs.value.slice(index + 1)
    ]
  }
}

const handleDeleteCrossItems = (e: KeyboardEvent, item: string) => {
  if ((e.target as HTMLInputElement).value) {
    return
  }
  keyValuePairs.value = keyValuePairs.value.filter((i) => i !== item)
}

const deleteItem = (item: string) => {
  keyValuePairs.value = keyValuePairs.value.filter((i) => i !== item)
}
</script>

<template>
  <ul class="label-list">
    <li v-for="(item, index) in keyValuePairs" :key="item">
      <span style="display: flex; align-items: center">
        <input
          class="item"
          type="text"
          :value="item"
          @keydown.enter="
            (e: KeyboardEvent) => editItem((e.target as HTMLInputElement).value, index)
          "
          @keydown.delete="(e: KeyboardEvent) => handleDeleteCrossItems(e, item)"
        />
        <button class="item-delete-btn" @click="() => deleteItem(item)">
          <X class="close-btn" />
        </button>
      </span>
    </li>
  </ul>
  <div
    v-if="
      !props.spec.autocompleter ||
      !props.spec.max_labels ||
      keyValuePairs.length < props.spec.max_labels
    "
  >
    <!-- In formLabel, the size on input is a fixed size -->
    <FormAutocompleter
      :size="inputSizes['MEDIUM'].width"
      :autocompleter="props.spec.autocompleter"
      :placeholder="props.spec.i18n.add_some_labels"
      :show="!error"
      :filter-on="keyValuePairs"
      :resest-input-on-add="true"
      @keydown.enter="
        (e: KeyboardEvent) => {
          const v = (e.target as HTMLInputElement).value
          if (v.length > 0) {
            validate(v)
          }
        }
      "
      @select="addItem"
    />
  </div>
  <div v-else class="error">{{ props.spec.i18n.max_labels_reached }}</div>
  <FormValidation :validation="validation"></FormValidation>
  <div v-if="error" class="error">{{ error }}</div>
</template>

<style scoped>
.label-list {
  list-style-type: none;
  padding: 0;
  margin: 0;

  li {
    width: fit-content;
    border-radius: 5px;
    background-color: var(--default-form-element-bg-color);
    margin: 5px 0;
    padding: 2px;

    &:focus-within {
      background-color: var(--default-form-element-border-color);
    }
  }
}

table.nform input {
  margin: 0;
  padding: 2px;
}

.item {
  height: 8px;
  background-color: var(--default-form-element-bg-color);

  &:focus {
    background-color: var(--default-form-element-border-color);
  }
}

.new-item {
  padding: 4px;
}

.error {
  margin: 0;
  padding: 5px;
  background-color: rgb(247, 65, 65);
  color: var(--font-color);
  display: block;
}

.item-delete-btn {
  cursor: pointer;
  margin: 0 5px;
  padding: 0;
  border-radius: 50%;
  width: 10px;
  height: 10px;
  border: none;

  &:hover {
    background-color: #c77777;
  }
}

.close-btn {
  width: 10px;
  height: 10px;
  margin: 0;
  padding: 1px;
  display: flex;
  justify-content: center;
  align-items: center;
  box-sizing: border-box;
}
</style>
