<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, useTemplateRef, computed, ref } from 'vue'
import { immediateWatch } from '@/lib/watch'

import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkHtml from '@/components/CmkHtml.vue'

export interface Suggestion {
  name: string
  title: string
}

type SuggestionsFixed = {
  type: 'fixed'
  suggestions: Array<Suggestion>
}

type SuggestionsFiltered = {
  type: 'filtered'
  suggestions: Array<Suggestion>
}

type Suggestions = SuggestionsFixed | SuggestionsFiltered

const {
  error = '',
  noResultsHint = '',
  suggestions,
  role
} = defineProps<{
  suggestions: Suggestions
  role: 'suggestion' | 'option'
  noResultsHint?: string
  error?: string
}>()

const showFilter = computed<boolean>(() => {
  return suggestions.type === 'filtered'
})

const emit = defineEmits<{
  select: [suggestion: Suggestion]
}>()

const suggestionRefs = useTemplateRef('suggestionRefs')
const filterString = ref<string>('')
const suggestionInputRef = ref<HTMLInputElement | null>(null)

const filteredSuggestions = ref<Array<Suggestion>>([])
const currentlySelectedElement: Ref<Suggestion | null> = ref(null) // null means first element

immediateWatch(
  () => suggestions.suggestions,
  (newValue: Suggestion[]) => {
    filteredSuggestions.value = newValue
  }
)
function isSuggestionSelected(suggestion: Suggestion, index: number): boolean {
  if (currentlySelectedElement.value === null && index === 0) {
    return true
  }
  if (suggestion.name === currentlySelectedElement.value?.name) {
    return true
  }
  return false
}

function scrollCurrentlySelectedIntoView(): void {
  if (suggestionRefs.value === null) {
    return
  }
  suggestionRefs.value[getCurrentlySelectedAsIndex()]?.scrollIntoView({ block: 'nearest' })
}

function getCurrentlySelectedAsIndex(): number {
  let currentlySelected = currentlySelectedElement.value
  if (currentlySelected === null) {
    if (!filteredSuggestions.value[0]) {
      throw new Error(
        'Internal error: CmkSuggestions: should select first element, but element not available'
      )
    }
    currentlySelected = filteredSuggestions.value[0]
  }
  const currentElement = filteredSuggestions.value
    .map((suggestion, index) => ({
      name: suggestion.name,
      index: index
    }))
    .find(({ name }) => currentlySelected.name === name)
  if (currentElement === undefined) {
    throw new Error('Internal error: CmkSuggestions: Could not find current element')
  }
  return currentElement.index
}

function filterUpdated(newFilterString: string) {
  filterString.value = newFilterString
  filteredSuggestions.value = suggestions.suggestions.filter(({ title }) =>
    title.toLowerCase().includes(newFilterString.toLowerCase())
  )
}

function onKeyEnter(event: InputEvent): void {
  event.stopPropagation()
  if (currentlySelectedElement.value === null) {
    selectSibilingElement(0)
  }
  if (currentlySelectedElement.value === null) {
    return
  }
  emit('select', currentlySelectedElement.value)
}

function onClickSuggestion(suggestion: Suggestion) {
  emit('select', suggestion)
}

function selectSibilingElement(direction: number) {
  if (!filteredSuggestions.value.length) {
    return
  }

  const currentIndex = getCurrentlySelectedAsIndex()

  currentlySelectedElement.value =
    filteredSuggestions.value[wrap(currentIndex + direction, filteredSuggestions.value.length)] ||
    null
}

function wrap(index: number, length: number): number {
  return (index + length) % length
}

function selectNextElement() {
  selectSibilingElement(+1)
  scrollCurrentlySelectedIntoView()
}
function selectPreviousElement() {
  selectSibilingElement(-1)
  scrollCurrentlySelectedIntoView()
}

function focus(): void {
  if (showFilter.value) {
    suggestionInputRef.value?.focus()
  } else if (filteredSuggestions.value.length > 0) {
    if (suggestionRefs.value && suggestionRefs.value[0]) {
      suggestionRefs.value[0].focus()
    }
  }
}

defineExpose({
  focus,
  selectNextElement,
  selectPreviousElement
})
</script>

<template>
  <ul
    class="cmk-suggestions"
    @keydown.enter.prevent="onKeyEnter"
    @keydown.down.prevent="selectNextElement"
    @keydown.up.prevent="selectPreviousElement"
  >
    <span :class="{ hidden: !showFilter, input: true }">
      <input
        ref="suggestionInputRef"
        v-model="filterString"
        type="text"
        @update:model-value="filterUpdated"
      />
    </span>
    <CmkScrollContainer :max-height="'200px'">
      <li v-if="error" class="cmk-suggestions--error"><CmkHtml :html="error" /></li>
      <li
        v-for="(suggestion, index) in filteredSuggestions"
        ref="suggestionRefs"
        :key="suggestion.name"
        tabindex="-1"
        :role="role"
        class="selectable"
        :class="{ selected: isSuggestionSelected(suggestion, index) }"
        @click.prevent="onClickSuggestion(suggestion)"
      >
        {{ suggestion.title }}
      </li>
      <li v-if="filteredSuggestions.length === 0 && noResultsHint !== ''">
        {{ noResultsHint }}
      </li>
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
}
.cmk-suggestions--error {
  background-color: var(--error-msg-bg-color);
}
</style>
