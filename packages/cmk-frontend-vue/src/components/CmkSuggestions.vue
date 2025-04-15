<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, nextTick, useTemplateRef, computed, ref } from 'vue'
import { immediateWatch } from '@/lib/watch'

import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkHtml from '@/components/CmkHtml.vue'

import { type Suggestion, ErrorResponse, Response } from './suggestions'

type SuggestionsFixed = {
  type: 'fixed'
  suggestions: Array<Suggestion>
}

type SuggestionsFiltered = {
  type: 'filtered'
  suggestions: Array<Suggestion>
}

type SuggestionsCallbackFiltered = {
  type: 'callback-filtered'
  querySuggestions: (query: string) => Promise<ErrorResponse | Response>
  getTitle?: (name: string) => Promise<ErrorResponse | string>
}

export type Suggestions = SuggestionsFixed | SuggestionsFiltered | SuggestionsCallbackFiltered

const {
  noResultsHint = '',
  suggestions,
  role
} = defineProps<{
  suggestions: Suggestions
  role: 'suggestion' | 'option'
  noResultsHint?: string
}>()

const showFilter = computed<boolean>(() => {
  return suggestions.type === 'filtered' || suggestions.type === 'callback-filtered'
})

const emit = defineEmits<{
  select: [suggestion: Suggestion]
  blur: []
}>()

const error = ref<string>('')
const suggestionRefs = useTemplateRef('suggestionRefs')
const filterString = ref<string>('')
const suggestionInputRef = ref<HTMLInputElement | null>(null)

const filteredSuggestions = ref<Array<Suggestion>>([])
const currentlySelectedElement: Ref<Suggestion | null> = ref(null) // null means first element

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
  const index = getCurrentlySelectedAsIndex()
  if (index === null) {
    return
  }
  suggestionRefs.value[index]?.scrollIntoView({ block: 'nearest' })
}

function getCurrentlySelectedAsIndex(): number | null {
  let currentlySelected = currentlySelectedElement.value
  if (currentlySelected === null) {
    if (!filteredSuggestions.value[0]) {
      return null
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
    return null
  }
  return currentElement.index
}

async function getSuggestions(
  suggestions: Suggestions,
  query: string
): Promise<Response | ErrorResponse> {
  switch (suggestions.type) {
    case 'filtered':
      return new Response(
        suggestions.suggestions.filter(({ title }) =>
          title.toLowerCase().includes(query.toLowerCase())
        )
      )
    case 'callback-filtered':
      return await suggestions.querySuggestions(query)
    case 'fixed':
      return new Response(suggestions.suggestions)
  }
}

immediateWatch(
  () => ({ newSuggestions: suggestions, newFilterString: filterString }),
  async ({ newSuggestions, newFilterString }) => {
    const result = await getSuggestions(newSuggestions, newFilterString.value)

    if (result instanceof ErrorResponse) {
      error.value = result.error
    } else {
      error.value = ''
      filteredSuggestions.value = result.choices
    }
  },
  { deep: 2 }
)

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
  if (currentIndex === null) {
    currentlySelectedElement.value = null
  } else {
    currentlySelectedElement.value =
      filteredSuggestions.value[wrap(currentIndex + direction, filteredSuggestions.value.length)] ||
      null
  }
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

async function focus(): Promise<void> {
  if (showFilter.value) {
    suggestionInputRef.value?.focus()
  } else if (filteredSuggestions.value.length > 0) {
    await nextTick()
    if (suggestionRefs.value === null || suggestionRefs.value[0] === undefined) {
      throw new Error('CmkSuggestions: internal: can not focus')
    }
    suggestionRefs.value[0].focus()
  }
}

function inputLostFocus(event: unknown) {
  // the click event is not triggered, so we have to use the native browser
  // events to figure out what element actually got clicked.
  if (suggestionRefs.value === null) {
    return
  }
  const elementClicked = (event as FocusEvent).relatedTarget
  for (const [index, suggestionRef] of suggestionRefs.value.entries()) {
    if (suggestionRef === elementClicked) {
      emit('select', filteredSuggestions.value[index]!)
      return
    }
  }
  emit('blur')
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
    role="listbox"
    @keydown.enter.prevent="onKeyEnter"
    @keydown.down.prevent="selectNextElement"
    @keydown.up.prevent="selectPreviousElement"
  >
    <span :class="{ hidden: !showFilter, input: true }">
      <input
        ref="suggestionInputRef"
        v-model="filterString"
        aria-label="filter"
        type="text"
        @blur="inputLostFocus"
        @keydown.escape.prevent="emit('blur')"
      />
    </span>
    <CmkScrollContainer :max-height="'200px'">
      <li v-if="error" class="cmk-suggestions--error"><CmkHtml :html="error" /></li>
      <!-- eslint-disable vue/valid-v-for vue/require-v-for-key since the index in suggestionRefs does not get correctly updated when using the suggestion name as key -->
      <li
        v-for="(suggestion, index) in filteredSuggestions"
        ref="suggestionRefs"
        tabindex="-1"
        :role="role"
        class="selectable"
        :class="{ selected: isSuggestionSelected(suggestion, index) }"
        @click="onClickSuggestion(suggestion)"
      >
        <!-- eslint-enable vue/valid-v-for vue/require-v-for-key -->
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
  box-sizing: border-box;
  border-radius: 0px;
  min-width: 100%;
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
