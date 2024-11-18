<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import { X } from 'lucide-vue-next'
import { onBeforeUpdate, ref, useTemplateRef, watch } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'

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

const error = ref<string | null>(null)
const filteredSuggestions = ref<string[]>([])
const inputValue = ref<string>('')
const showSuggestions = ref<boolean>(false)
const selectedSuggestionIndex = ref<number>(-1)

const inputField = useTemplateRef<HTMLInputElement>('inputField')

type AutocompleterResponse = Record<'choices', [string, string][]>
const [autocompleterInput, autocompleterOutput] = setupAutocompleter<AutocompleterResponse>(
  props.spec.autocompleter || null
)

watch(inputValue, (newValue) => {
  showSuggestions.value = inputValue.value ? true : false
  autocompleterInput.value = newValue
})

watch(autocompleterOutput, (newValue) => {
  if (newValue === undefined) {
    return
  }
  filteredSuggestions.value = newValue.choices
    .map((element: [string, string]) => element[0])
    .filter((element: string) => element.length > 0)
    .filter((element: string) => !keyValuePairs.value.includes(element))
    .splice(0, 15)
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

const handleAddItem = (e: KeyboardEvent) => {
  const value = (e.target as HTMLInputElement).value
  if (value) {
    addItem(value)
  }
  inputReset()
}

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
  inputFocus()
}

const handleDeleteCrossItems = (e: KeyboardEvent, item: string) => {
  if ((e.target as HTMLInputElement).value) {
    return
  }

  keyValuePairs.value = keyValuePairs.value.filter((i) => i !== item)
  inputFocus()
}

const handleCloseList = (suggestion: string) => {
  inputValue.value = suggestion
  inputReset()
  inputFocus()
  addItem(suggestion)
}

const deleteItem = (item: string) => {
  keyValuePairs.value = keyValuePairs.value.filter((i) => i !== item)
}

const setBlur = (isSet: boolean) => {
  setTimeout(() => {
    showSuggestions.value = isSet
  }, 200)
}

const inputReset = () => {
  inputValue.value = ''
}

const inputFocus = () => {
  if (inputField.value) {
    inputField.value.focus()
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (selectedSuggestionIndex.value < filteredSuggestions.value.length - 1) {
      selectedSuggestionIndex.value++
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (selectedSuggestionIndex.value > 0) {
      selectedSuggestionIndex.value--
    }
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (selectedSuggestionIndex.value >= 0) {
      const suggestion = filteredSuggestions.value[selectedSuggestionIndex.value]
      if (suggestion) {
        handleCloseList(suggestion)
      }
    }
  }
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
    v-if="!props.spec.max_labels || keyValuePairs.length < props.spec.max_labels"
    class="autocomplete"
  >
    <input
      ref="inputField"
      v-model="inputValue"
      class="item new-item"
      type="text"
      autocomplete="on"
      :placeholder="props.spec.i18n.add_some_labels"
      @keydown.enter="handleAddItem"
      @focus="() => setBlur(true)"
      @blur="() => setBlur(false)"
      @keydown="handleKeyDown"
    />
    <Transition name="fade">
      <ul
        v-if="
          filteredSuggestions.length > 0 &&
          !filteredSuggestions.includes(inputValue) &&
          !error &&
          !!showSuggestions &&
          !!inputValue
        "
        class="suggestions"
        @blur="showSuggestions = false"
      >
        <li
          v-for="(option, index) in filteredSuggestions"
          :key="option"
          :class="{ selected: index === selectedSuggestionIndex }"
          @click="() => handleCloseList(option)"
        >
          {{ option }}
        </li>
      </ul>
    </Transition>
  </div>
  <div v-else class="error">{{ props.spec.i18n.max_labels_reached }}</div>
  <FormValidation :validation="validation"></FormValidation>

  <Transition name="fade">
    <div v-if="error" class="error">{{ error }}</div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.2s ease-out,
    transform 0.2s ease-out;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

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
  }
}

table.nform input {
  margin: 0;
  padding: 2px;
}

.item {
  height: 8px;
  background-color: var(--default-form-element-bg-color);
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
  transition: background-color 0.3s;

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

.autocomplete {
  position: relative;
}

.suggestions {
  position: absolute;
  z-index: 1;
  color: var(--font-color);
  background-color: var(--default-form-element-bg-color);
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
  max-width: fit-content;
  margin: 0;
  padding: 0 16px 0 0;
  list-style-type: none;

  li {
    padding: 4px 8px;
    cursor: pointer;

    &:hover,
    &.selected {
      color: var(--default-select-hover-color);
    }
  }
}
</style>
