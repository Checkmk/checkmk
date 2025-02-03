<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'
import CmkSuggestions from '@/components/CmkSuggestions.vue'
import useClickOutside from '@/lib/useClickOutside'
import { useId } from '@/form/utils'

const props = defineProps<{
  id?: string
  placeholder: string
  autocompleter?: Autocompleter | null
  filterOn: string[]
  size: number
  resetInputOnAdd: boolean
  allowNewValueInput?: boolean
}>()

type Suggestion = [string, string]
const inputValue = defineModel<string>()
const visibleInputValue = ref<string>('')

type AutocompleterResponse = Record<'choices', Suggestion[]>
const { input: autocompleterInput, output: autocompleterOutput } =
  setupAutocompleter<AutocompleterResponse>(() => props.autocompleter || null)
const filteredSuggestions = ref<Suggestion[]>([])
const suggestionsRef = ref<InstanceType<typeof CmkSuggestions> | null>(null)
const showSuggestions = ref<boolean>(false)

const selectFirstSuggestion = () => {
  if (filteredSuggestions.value.length > 0) {
    const suggestion = filteredSuggestions.value[0]
    if (suggestion) {
      selectSuggestion(suggestion)
    }
  }
}

const selectSuggestion = (suggestion: Suggestion) => {
  inputValue.value = suggestion[0]
  visibleInputValue.value = suggestion[1]
  if (props.resetInputOnAdd) {
    resetVisibleInput()
  }
  showSuggestions.value = false
}

const deleteSelection = () => {
  inputValue.value = ''
  resetVisibleInput()
}

const resetVisibleInput = () => {
  visibleInputValue.value = ''
  autocompleterInput.value = ''
}

onMounted(() => {
  if (inputValue.value) {
    visibleInputValue.value = inputValue.value
  }
})

watch(autocompleterOutput, (newValue) => {
  if (newValue === undefined) {
    return
  }
  filteredSuggestions.value = []

  // If new value input is allowed and the input is not the title to one of the given autocompleter
  // choices, add the input as a new choice
  if (props.allowNewValueInput && visibleInputValue.value.length > 0) {
    filteredSuggestions.value = newValue.choices.find(
      (choice) => choice[1] === visibleInputValue.value
    )
      ? []
      : [[visibleInputValue.value, visibleInputValue.value]]
  }

  filteredSuggestions.value.push(
    ...newValue.choices
      .filter((element: Suggestion) => element[0].length > 0 && element[1].length > 0)
      .filter((element: Suggestion) => !props.filterOn.includes(element[0]))
  )
})

const updateInput = (ev: Event) => {
  const value = (ev.target as HTMLInputElement).value
  autocompleterInput.value = value
  if (props.allowNewValueInput) {
    inputValue.value = value
  }
  showSuggestions.value = true
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
          () => {
            if (autocompleterInput === undefined) autocompleterInput = ''
            showSuggestions = true
          }
        "
        @input="updateInput"
        @keydown.down.prevent="
          () => {
            suggestionsRef?.focus()
            suggestionsRef?.advance()
          }
        "
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
      v-if="filteredSuggestions.length > 0 && !!showSuggestions"
      ref="suggestionsRef"
      role="suggestion"
      :suggestions="
        filteredSuggestions.map((suggestion) => ({ name: suggestion[0], title: suggestion[1] }))
      "
      :on-select="(suggestion) => selectSuggestion([suggestion.name, suggestion.title])"
      :show-filter="false"
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
