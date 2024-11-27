<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'
import type { Autocompleter } from '../vue_formspec_components'

const props = defineProps<{
  placeholder: string
  show: boolean
  autocompleter: Autocompleter | undefined
  filterOn: string[]
}>()

const emit = defineEmits<{
  (e: 'itemSelected', value: string): void
}>()

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
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    if (selectedSuggestionIndex.value >= 0) {
      const suggestion = filteredSuggestions.value[selectedSuggestionIndex.value]
      if (suggestion) {
        inputValue.value = suggestion
        selectedSuggestionIndex.value = -1
      }
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

const handleFocus = () => {
  setBlur(true)
}

const handleBlur = () => {
  setBlur(false)
}

const handleAddItem = (e: KeyboardEvent) => {
  if (selectedSuggestionIndex.value >= 0) {
    inputReset()
    return
  }
  const value = (e.target as HTMLInputElement).value
  if (value) {
    emit('itemSelected', value)
  }
  inputReset()
}

const handleCloseList = (item: string) => {
  selectedSuggestionIndex.value = -1
  inputValue.value = item
  inputReset()
  inputFocus()
  emit('itemSelected', item)
}

const handleListBlur = () => {
  showSuggestions.value = false
}

const inputReset = () => {
  inputValue.value = ''
}

const inputFocus = () => {
  if (inputField.value) {
    inputField.value.focus()
  }
}

const setBlur = (isSet: boolean) => {
  setTimeout(() => {
    showSuggestions.value = isSet
  }, 200)
}

const inputValue = ref('')
type AutocompleterResponse = Record<'choices', [string, string][]>
const [autocompleterInput, autocompleterOutput] = setupAutocompleter<AutocompleterResponse>(
  props.autocompleter || null
)

const filteredSuggestions = ref<string[]>([])
const inputField = useTemplateRef<HTMLInputElement>('inputField')
const showSuggestions = ref<boolean>(false)
const selectedSuggestionIndex = ref<number>(-1)

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
    .filter((element: string) => !props.filterOn.includes(element))
    .splice(0, 15)
})
</script>

<template>
  <div class="autocomplete">
    <input
      ref="inputField"
      v-model="inputValue"
      class="item new-item"
      type="text"
      autocomplete="on"
      :placeholder="props.placeholder"
      @keydown.enter="handleAddItem"
      @focus="handleFocus"
      @blur="handleBlur"
      @keydown="handleKeyDown"
    />
    <Transition name="fade">
      <ul
        v-if="
          props.show &&
          filteredSuggestions.length > 0 &&
          !filteredSuggestions.includes(inputValue) &&
          !!inputValue &&
          !!showSuggestions
        "
        class="suggestions"
        @blur="handleListBlur"
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
  color: var(--default-text-color);
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
  color: var(--default-text-color);
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
