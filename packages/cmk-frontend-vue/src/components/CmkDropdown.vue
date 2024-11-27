<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, nextTick, ref, watch, type Ref } from 'vue'
import CmkButton from './CmkButton.vue'
import useClickOutside from '@/lib/useClickOutside'

export interface DropdownOption {
  name: string
  title: string
}

const {
  inputHint = '',
  noResultsHint = '',
  disabled = false,
  componentId = '',
  noElementsText = '',
  options,
  showFilter
} = defineProps<{
  options: DropdownOption[]
  showFilter: boolean
  inputHint?: string
  noResultsHint?: string
  disabled?: boolean
  componentId?: string
  noElementsText?: string
}>()

const vClickOutside = useClickOutside()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const selectedOptionTitle = computed(
  () => options.find(({ name }) => name === selectedOption.value)?.title ?? inputHint
)

const suggestionsShown = ref(false)
const suggestionInputRef = ref<HTMLInputElement | null>(null)
const comboboxButtonRef = ref<HTMLButtonElement | null>(null)
const optionRefs = ref<(HTMLLIElement | null)[]>([])

const filterString = ref('')
const filteredOptions = ref<number[]>(options.map((_, index) => index))
const selectedSuggestionOptionIndex: Ref<number | null> = ref(options.length > 0 ? 0 : null)

watch(filterString, (newFilterString) => {
  filteredOptions.value = options
    .map((option, index) => ({
      option,
      index
    }))
    .filter(({ option }) => option.title.toLowerCase().includes(newFilterString.toLowerCase()))
    .map(({ index }) => index)
  selectedSuggestionOptionIndex.value = filteredOptions.value[0] ?? null
})

function showSuggestions(): void {
  if (!disabled && options.length > 0) {
    suggestionsShown.value = !suggestionsShown.value
    filterString.value = ''
    filteredOptions.value = options.map((_, index) => index)
    selectedSuggestionOptionIndex.value = filteredOptions.value[0] ?? null
    nextTick(() => {
      suggestionInputRef.value?.focus()
    })
  }
}

function hideSuggestions(): void {
  suggestionsShown.value = false
  comboboxButtonRef.value?.focus()
}

function selectOption(optionIndex: number): void {
  selectedOption.value = options[optionIndex]?.name ?? null
  hideSuggestions()
}

function selectSuggestion(filteredOptionIndex: number | null): void {
  if (filteredOptionIndex === null) {
    selectedSuggestionOptionIndex.value = null
    return
  }
  const optionIndex = filteredOptions.value[filteredOptionIndex]
  if (optionIndex === undefined) {
    throw new Error('Invalid filtered option index')
  }
  selectedSuggestionOptionIndex.value = optionIndex
  nextTick(() => {
    optionRefs.value[optionIndex]?.scrollIntoView({ block: 'nearest' })
  })
}

function keyEnter(event: InputEvent): void {
  event.preventDefault()
  event.stopPropagation()
  if (selectedSuggestionOptionIndex.value === null) {
    return
  }
  selectOption(selectedSuggestionOptionIndex.value)
}

function moveSuggestion(amount: number): void {
  if (selectedSuggestionOptionIndex.value === null) {
    return
  }
  const selectedFilteredOptionIndex = filteredOptions.value.findIndex(
    (index) => index === selectedSuggestionOptionIndex.value
  )
  if (selectedFilteredOptionIndex === -1) {
    throw new Error('Selected suggestion option index not found in filtered options')
  }
  selectSuggestion(
    filteredOptions.value[
      wrap(selectedFilteredOptionIndex + amount, filteredOptions.value.length)
    ] ?? null
  )
}

function wrap(index: number, length: number): number {
  return (index + length) % length
}
</script>

<template>
  <div
    v-click-outside="
      () => {
        if (suggestionsShown) suggestionsShown = false
      }
    "
    class="cmk-dropdown"
  >
    <CmkButton
      v-if="options.length > 0"
      :id="componentId"
      ref="comboboxButtonRef"
      role="combobox"
      :aria-label="selectedOptionTitle"
      :aria-expanded="suggestionsShown"
      :class="{ 'cmk-dropdown__button': true, disabled: disabled || options.length === 0 }"
      :variant="'transparent'"
      @click.prevent="showSuggestions"
    >
      <div>{{ selectedOptionTitle }}</div>
    </CmkButton>
    <span v-else>{{ noElementsText }}</span>
    <ul
      v-if="!!suggestionsShown"
      class="cmk-dropdown__suggestions"
      @keydown.escape.prevent="hideSuggestions"
      @keydown.tab.prevent="hideSuggestions"
      @keydown.enter="keyEnter"
      @keydown.down.prevent="() => moveSuggestion(1)"
      @keydown.up.prevent="() => moveSuggestion(-1)"
    >
      <span :class="{ hidden: !showFilter, input: true }">
        <input ref="suggestionInputRef" v-model="filterString" type="text"
      /></span>
      <div class="options-container">
        <template v-for="(option, index) in options" :key="option.name">
          <li
            v-show="filteredOptions.includes(index)"
            :ref="(el) => (optionRefs[index] = el as HTMLLIElement)"
            role="option"
            :class="{ selected: index === selectedSuggestionOptionIndex, selectable: true }"
            @click.prevent="() => selectOption(index)"
          >
            {{ option.title }}
          </li>
        </template>
        <li v-if="filteredOptions.length === 0 && noResultsHint !== ''">
          {{ noResultsHint }}
        </li>
      </div>
    </ul>
  </div>
</template>

<style scoped>
.cmk-dropdown {
  display: inline-block;
  position: relative;
}

.cmk-dropdown__button {
  cursor: pointer;
  background-color: var(--default-form-element-bg-color);
  margin: 0;
  padding: 3px 2.5em 3px 6px;
  background-image: var(--icon-select-arrow);
  background-position: right 50%;
  background-repeat: no-repeat;
  background-size: 20px 11px;
  -webkit-appearance: none;
  -moz-appearance: none;

  &:hover {
    background-color: var(--input-hover-bg-color);
  }

  &.disabled {
    cursor: auto;
    color: var(--font-color-dimmed);
    &:hover {
      background-color: var(--default-form-element-bg-color);
    }
  }
}

.cmk-dropdown__suggestions {
  position: absolute;
  z-index: 1;
  color: var(--font-color);
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-6);
  border-radius: 0px;
  max-width: fit-content;
  margin: 0;
  padding: 0;
  list-style-type: none;

  span.input {
    display: flex;
    padding: 4px;

    &.hidden {
      display: none;
    }
  }

  input {
    width: 100%;
    margin: 0;
    background: var(--ux-theme-3);
  }

  li {
    padding: 6px;
    cursor: default;

    &.selectable {
      cursor: pointer;
      &:hover,
      &.selected {
        color: var(--default-select-hover-color);
      }
    }
  }

  .options-container {
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
  }
}
</style>
