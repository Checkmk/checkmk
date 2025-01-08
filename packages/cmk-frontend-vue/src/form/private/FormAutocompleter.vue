<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue'
import { setupAutocompleter } from '@/form/components/utils/autocompleter'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { X } from 'lucide-vue-next'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

const props = defineProps<{
  id?: string
  placeholder: string
  show: boolean
  autocompleter?: Autocompleter | null
  filterOn: string[]
  size: number
  resestInputOnAdd: boolean
}>()

const inputValue = defineModel<string>()

const emit = defineEmits<{
  (e: 'select', value: string): void
}>()

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (selectedSuggestionIndex.value === filteredSuggestions.value.length - 1) {
      selectedSuggestionIndex.value = 0
    } else if (selectedSuggestionIndex.value < filteredSuggestions.value.length - 1) {
      selectedSuggestionIndex.value++
    }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (selectedSuggestionIndex.value === 0) {
      selectedSuggestionIndex.value = filteredSuggestions.value.length - 1
    } else if (selectedSuggestionIndex.value > 0) {
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

const handleAddItem = (e: KeyboardEvent) => {
  if (selectedSuggestionIndex.value >= 0) {
    inputReset()
    return
  }
  const value = (e.target as HTMLInputElement).value
  if (value) {
    emit('select', value)
  }
  inputReset()

  if (!props.resestInputOnAdd) {
    setBlur(false)
  }
}

const handleCloseList = (item: string) => {
  selectedSuggestionIndex.value = -1
  inputValue.value = item
  inputReset()
  setBlur(false)
  emit('select', item)
}

const handleListBlur = () => {
  showSuggestions.value = false
}

const inputReset = () => {
  if (props.resestInputOnAdd) {
    inputValue.value = ''
  }
}

const setBlur = (isSet: boolean) => {
  autocompleteFocus.value = isSet
  setTimeout(() => {
    showSuggestions.value = isSet
  }, 200)
}

type AutocompleterResponse = Record<'choices', [string, string][]>
const {
  input: autocompleterInput,
  focus: autocompleteFocus,
  output: autocompleterOutput
} = setupAutocompleter<AutocompleterResponse>(() => props.autocompleter || null)

const filteredSuggestions = ref<string[]>([])
const inputField = useTemplateRef<HTMLInputElement>('inputField')
const showSuggestions = ref<boolean>(false)
const selectedSuggestionIndex = ref<number>(-1)

watch(inputValue, (newValue) => {
  showSuggestions.value = inputValue.value ? true : false
  autocompleterInput.value = newValue || ''
})

watch(autocompleterOutput, (newValue) => {
  if (newValue === undefined) {
    return
  }
  filteredSuggestions.value = newValue.choices
    .map((element: [string, string]) => element[0])
    .filter((element: string) => element.length > 0)
    .filter((element: string) => !props.filterOn.includes(element))
})
</script>

<template>
  <div class="autocomplete">
    <span style="display: flex; align-items: center">
      <input
        :id="props.id ?? 'autocomplete'"
        ref="inputField"
        v-model="inputValue"
        class="item new-item"
        type="text"
        autocomplete="on"
        :size="props.size"
        :placeholder="props.placeholder"
        @keydown.enter="handleAddItem"
        @focus="() => setBlur(true)"
        @blur="() => setBlur(false)"
        @keydown="handleKeyDown"
      />
      <X
        :style="{ opacity: !!inputValue ? 1 : 0, cursor: !!inputValue ? 'pointer' : 'unset' }"
        class="item-delete-btn"
        @click="() => (inputValue = '')"
      />
    </span>

    <CmkScrollContainer>
      <ul
        v-if="props.show && filteredSuggestions.length > 0 && !!showSuggestions"
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
    </CmkScrollContainer>
  </div>
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
  }
}

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

  &:hover {
    background-color: #c77777;
  }
}

.autocomplete {
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

.suggestions {
  position: absolute;
  z-index: 1;
  color: var(--default-text-color);
  background-color: var(--default-form-element-bg-color);
  border-radius: 4px;
  max-height: 200px;
  width: 100%;
  overflow-y: auto;
  margin: 0;
  padding: 0;
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
