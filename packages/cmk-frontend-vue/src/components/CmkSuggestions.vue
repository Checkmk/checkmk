<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, nextTick, ref, watch } from 'vue'
import CmkScrollContainer from './CmkScrollContainer.vue'

export interface Suggestion {
  name: string
  title: string
}

const {
  noResultsHint = '',
  onSelect,
  suggestions,
  showFilter
} = defineProps<{
  suggestions: Suggestion[]
  onSelect: (suggestion: Suggestion) => void
  showFilter: boolean
  noResultsHint?: string
}>()

const suggestionInputRef = ref<HTMLInputElement | null>(null)
const suggestionRefs = ref<(HTMLLIElement | null)[]>([])

const filterString = ref('')
const filteredSuggestions = ref<number[]>(suggestions.map((_, index) => index))
const selectedSuggestionIndex: Ref<number | null> = ref(suggestions.length > 0 ? 0 : null)

watch(filterString, (newFilterString) => {
  filteredSuggestions.value = suggestions
    .map((suggestion, index) => ({
      suggestion,
      index
    }))
    .filter(({ suggestion }) =>
      suggestion.title.toLowerCase().includes(newFilterString.toLowerCase())
    )
    .map(({ index }) => index)
  selectedSuggestionIndex.value = filteredSuggestions.value[0] ?? null
})

function selectSuggestion(suggestionIndex: number): void {
  const selection = suggestions[suggestionIndex]
  if (selection) {
    onSelect(selection)
  }
}

function setActiveSuggestion(filteredSuggestionIndex: number | null): void {
  if (filteredSuggestionIndex === null) {
    selectedSuggestionIndex.value = null
    return
  }
  const suggestionIndex = filteredSuggestions.value[filteredSuggestionIndex]
  if (suggestionIndex === undefined) {
    throw new Error('Invalid filtered suggestion index')
  }
  selectedSuggestionIndex.value = suggestionIndex
  // eslint-disable-next-line @typescript-eslint/no-floating-promises
  nextTick(() => {
    suggestionRefs.value[suggestionIndex]?.scrollIntoView({ block: 'nearest' })
  })
}

function keyEnter(event: InputEvent): void {
  event.stopPropagation()
  if (selectedSuggestionIndex.value === null) {
    return
  }
  selectSuggestion(selectedSuggestionIndex.value)
}

function moveSuggestion(amount: number): void {
  if (selectedSuggestionIndex.value === null) {
    return
  }
  const selectedFilteredSuggestionIndex = filteredSuggestions.value.findIndex(
    (index) => index === selectedSuggestionIndex.value
  )
  if (selectedFilteredSuggestionIndex === -1) {
    throw new Error('Selected suggestion suggestion index not found in filtered suggestions')
  }
  setActiveSuggestion(
    filteredSuggestions.value[
      wrap(selectedFilteredSuggestionIndex + amount, filteredSuggestions.value.length)
    ] ?? null
  )
}

function wrap(index: number, length: number): number {
  return (index + length) % length
}

function focus(): void {
  if (showFilter) {
    suggestionInputRef.value?.focus()
  } else if (suggestions.length > 0) {
    suggestionRefs.value[0]?.focus()
  }
}

defineExpose({
  focus
})
</script>

<template>
  <ul
    class="cmk-suggestions"
    @keydown.enter.prevent="keyEnter"
    @keydown.down.prevent="() => moveSuggestion(1)"
    @keydown.up.prevent="() => moveSuggestion(-1)"
  >
    <span :class="{ hidden: !showFilter, input: true }">
      <input ref="suggestionInputRef" v-model="filterString" type="text"
    /></span>
    <CmkScrollContainer>
      <div class="cmk-suggestions-container">
        <template v-for="(suggestion, index) in suggestions" :key="suggestion.name">
          <li
            v-show="filteredSuggestions.includes(index)"
            :ref="(el) => (suggestionRefs[index] = el as HTMLLIElement)"
            tabindex="-1"
            role="suggestion"
            :class="{ selected: index === selectedSuggestionIndex, selectable: true }"
            @click.prevent="() => selectSuggestion(index)"
          >
            {{ suggestion.title }}
          </li>
        </template>
        <li v-if="filteredSuggestions.length === 0 && noResultsHint !== ''">
          {{ noResultsHint }}
        </li>
      </div>
    </CmkScrollContainer>
  </ul>
</template>

<style scoped>
.cmk-suggestions {
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

    &:focus {
      outline: none;
    }

    &.selectable {
      cursor: pointer;
      &.selected {
        color: var(--default-select-focus-color);
      }
      &:hover {
        color: var(--default-select-hover-color);
      }
    }
  }

  .cmk-suggestions-container {
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
  }
}
</style>
