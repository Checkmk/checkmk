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

const props = defineProps({
  options: {
    type: Array as () => DropdownOption[],
    required: true
  },
  input_hint: {
    type: String,
    default: ''
  },
  no_results_hint: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  componentId: {
    type: String,
    default: ''
  }
})

const vClickOutside = useClickOutside()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const selectedOptionTitle = computed(
  () =>
    props.options.find((option) => option.name === selectedOption.value)?.title ?? props.input_hint
)

const suggestionsShown = ref(false)
const suggestionInputRef = ref<HTMLInputElement | null>(null)
const comboboxButtonRef = ref<HTMLButtonElement | null>(null)

const filterString = ref('')
const filteredOptions = ref<DropdownOption[]>(props.options)
const selectedSuggestionName: Ref<string | null> = ref(props.options[0]?.name ?? null)

watch(filterString, (newFilterString) => {
  filteredOptions.value = props.options.filter((option) =>
    option.title.toLowerCase().includes(newFilterString.toLowerCase())
  )
  selectedSuggestionName.value = filteredOptions.value[0]?.name ?? null
})

function showSuggestions(): void {
  if (!props.disabled && props.options.length > 0) {
    suggestionsShown.value = !suggestionsShown.value
    filterString.value = ''
    filteredOptions.value = props.options
    selectedSuggestionName.value = Object.values(props.options)[0]?.name ?? null
    nextTick(() => {
      suggestionInputRef.value?.focus()
    })
  }
}

function hideSuggestions(): void {
  suggestionsShown.value = false
  comboboxButtonRef.value?.focus()
}

function selectOption(option: DropdownOption): void {
  selectedOption.value = option.name
  hideSuggestions()
}

function keyEnter(event: InputEvent): void {
  event.preventDefault()
  event.stopPropagation()
  const selectedSuggestion = filteredOptions.value.find(
    (o) => o.name === selectedSuggestionName.value
  )
  if (selectedSuggestion) {
    selectOption(selectedSuggestion)
  }
}

function keyDown(): void {
  const index = filteredOptions.value.findIndex((o) => o.name === selectedSuggestionName.value)
  selectedSuggestionName.value =
    filteredOptions.value[wrap(index + 1, filteredOptions.value.length)]?.name ?? null
}

function keyUp(): void {
  const index = filteredOptions.value.findIndex((o) => o.name === selectedSuggestionName.value)
  selectedSuggestionName.value =
    filteredOptions.value[wrap(index - 1, filteredOptions.value.length)]?.name ?? null
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
  >
    <CmkButton
      :id="componentId"
      ref="comboboxButtonRef"
      role="combobox"
      :aria-label="selectedOptionTitle"
      :aria-expanded="suggestionsShown"
      :class="{ 'drop-down': true, disabled: props.disabled || props.options.length === 0 }"
      :variant="'transparent'"
      @click.prevent="showSuggestions"
    >
      <div>{{ selectedOptionTitle }}</div>
    </CmkButton>
    <ul
      v-if="!!suggestionsShown"
      class="suggestions"
      @keydown.escape.prevent="hideSuggestions"
      @keydown.tab.prevent="hideSuggestions"
      @keydown.enter="keyEnter"
      @keydown.down.prevent="keyDown"
      @keydown.up.prevent="keyUp"
    >
      <span class="input">
        <input ref="suggestionInputRef" v-model="filterString" type="text"
      /></span>
      <li
        v-for="option in filteredOptions"
        :key="option.name"
        role="option"
        :class="{ selected: option.name === selectedSuggestionName, selectable: true }"
        @click.prevent="() => selectOption(option)"
      >
        {{ option.title }}
      </li>
      <li v-if="filteredOptions.length === 0 && props.no_results_hint !== ''">
        {{ props.no_results_hint }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
div {
  display: inline-block;
}

.drop-down {
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

.suggestions {
  position: absolute;
  z-index: 1;
  color: var(--font-color);
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-6);
  border-radius: 0px;
  max-height: 200px;
  overflow-y: auto;
  max-width: fit-content;
  margin: 0;
  padding: 0;
  list-style-type: none;

  span.input {
    display: flex;
    padding: 4px;
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
}
</style>
