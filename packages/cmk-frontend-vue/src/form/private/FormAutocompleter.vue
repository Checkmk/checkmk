<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'
import CmkSuggestions from '@/components/CmkSuggestions.vue'
import useClickOutside from '@/lib/useClickOutside'
import { useId } from '@/form/utils'

import {
  fetchSuggestions,
  type Suggestion,
  ErrorResponse
} from '@/form/components/utils/autocompleter'

const props = defineProps<{
  id?: string
  placeholder: string
  autocompleter?: Autocompleter
  filterOn: string[]
  size: number
  resetInputOnAdd: boolean
  allowNewValueInput?: boolean
}>()

const inputValue = defineModel<string>()
const visibleInputValue = ref<string>('')

const autocompleterError = ref<string>('')

const filteredSuggestions = ref<Suggestion[]>([])
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const showSuggestions = ref<boolean>(false)

const selectFirstSuggestion = async () => {
  if (filteredSuggestions.value.length > 0) {
    const suggestion = filteredSuggestions.value[0]
    if (suggestion) {
      await selectSuggestion(suggestion)
    }
  }
}

const selectSuggestion = async (suggestion: Suggestion) => {
  inputValue.value = suggestion.name
  visibleInputValue.value = suggestion.title
  if (props.resetInputOnAdd) {
    await resetVisibleInput()
  }
  showSuggestions.value = false
}

const deleteSelection = async () => {
  inputValue.value = ''
  await resetVisibleInput()
}

const resetVisibleInput = async () => {
  visibleInputValue.value = ''
  await updateSuggestions('')
}

onMounted(() => {
  if (inputValue.value) {
    visibleInputValue.value = inputValue.value
  }
})

async function updateSuggestions(query: string) {
  if (props.autocompleter === undefined) {
    return
  }
  autocompleterError.value = ''
  const newValue = await fetchSuggestions(props.autocompleter, query)
  if (newValue instanceof ErrorResponse) {
    autocompleterError.value = newValue.error
    return
  }
  filteredSuggestions.value = []

  // If new value input is allowed and the input is not the title to one of the given autocompleter
  // choices, add the input as a new choice
  if (props.allowNewValueInput && visibleInputValue.value.length > 0) {
    if (newValue.choices.find((choice) => choice.title === visibleInputValue.value)) {
      filteredSuggestions.value = [
        { name: visibleInputValue.value, title: visibleInputValue.value }
      ]
    }
  }

  filteredSuggestions.value.push(
    ...newValue.choices
      .filter((element: Suggestion) => element.name.length > 0 && element.title.length > 0)
      .filter((element: Suggestion) => !props.filterOn.includes(element.name))
  )
}

// TODO: replace with vuejs update mechanism
const updateInput = async (ev: Event) => {
  const value = (ev.target as HTMLInputElement).value
  await updateSuggestions(value)
  if (props.allowNewValueInput) {
    inputValue.value = value
  }
  showSuggestions.value = true
}

function onInputKeyUpDown() {
  suggestionsRef.value?.focus()
  suggestionsRef.value?.selectPreviousElement()
}

function onInputKeyDownDown() {
  suggestionsRef.value?.focus()
  suggestionsRef.value?.selectNextElement()
}

const vClickOutside = useClickOutside()
const componentId = useId()
</script>

<template>
  <div
    v-click-outside="
      () => {
        showSuggestions = false
        if (inputValue === '') {
          visibleInputValue = ''
        }
      }
    "
    class="form-autocompleter"
  >
    <span style="display: flex; align-items: center">
      <input
        :id="props.id ?? componentId"
        v-model="visibleInputValue"
        class="item new-item"
        type="text"
        autocomplete="on"
        :size="props.size"
        :placeholder="props.placeholder"
        @keydown.enter.prevent="selectFirstSuggestion"
        @focus="
          async () => {
            await updateSuggestions('')
            showSuggestions = true
          }
        "
        @input="updateInput"
        @keydown.up.prevent="onInputKeyUpDown"
        @keydown.down.prevent="onInputKeyDownDown"
      />
      <X
        :style="{
          opacity: !!visibleInputValue ? 1 : 0,
          cursor: !!visibleInputValue ? 'pointer' : 'unset'
        }"
        class="item-delete-btn"
        @click="deleteSelection"
      />
    </span>
    <CmkSuggestions
      v-if="(filteredSuggestions.length > 0 || autocompleterError) && !!showSuggestions"
      ref="suggestionsRef"
      role="suggestion"
      :error="autocompleterError"
      :suggestions="filteredSuggestions"
      :show-filter="false"
      @select="(suggestion) => selectSuggestion(suggestion)"
    />
  </div>
</template>

<style scoped>
table.nform input {
  margin: 0 5px;
  padding: 2px;
}

.item {
  background-color: var(--default-form-element-bg-color);

  &:focus,
  &:active {
    background-color: var(--default-form-element-border-color);
  }
}

.new-item {
  padding: 4px;
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

.form-autocompleter {
  position: relative;
  width: fit-content;
  border-radius: 5px;

  background-color: var(--default-form-element-bg-color);
  margin: 0;
  padding: 0;

  &:focus-within {
    background-color: var(--default-form-element-border-color);
  }
}
</style>
