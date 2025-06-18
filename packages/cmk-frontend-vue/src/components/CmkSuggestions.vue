<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, useTemplateRef, computed, ref, type Ref } from 'vue'
import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkScrollContainer from './CmkScrollContainer.vue'
import CmkHtml from '@/components/CmkHtml.vue'

import { type Suggestion, ErrorResponse, Response } from './suggestions'

const { t } = usei18n('cmk-suggestions')

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
  'request-close-suggestions': []
  blur: []
}>()

const selectedOption = defineModel<string | null>('selectedOption', { required: true })
const error = ref<string>('')
const suggestionRefs = useTemplateRef('suggestionRefs')
const filterString = ref<string>('')
const suggestionInputRef = ref<HTMLInputElement | null>(null)
const firstSelectableIndex = ref(0)

const filteredSuggestions = ref<Array<Suggestion>>([])
const highlightedOption: Ref<Suggestion | null> = ref(null) // null means no selection, (no selectable elements)

function isSuggestionHighlighted(suggestion: Suggestion, index: number): boolean {
  if (
    index === firstSelectableIndex.value &&
    (highlightedOption.value === null || highlightedOption.value.name === null)
  ) {
    return true
  }
  return suggestion.name === highlightedOption.value?.name
}

function scrollCurrentlySelectedIntoView(): void {
  if (suggestionRefs.value === null) {
    return
  }
  const index = findSuggestionAsIndex(filteredSuggestions.value, highlightedOption.value)
  if (index === null) {
    return
  }
  suggestionRefs.value[index]?.scrollIntoView({ block: 'nearest' })
}

function findSuggestionAsIndex(
  suggestions: Array<Suggestion>,
  suggestion: Suggestion | null
): number | null {
  if (suggestion === null) {
    return null
  }
  const currentElement = suggestions
    .map((suggestion, index) => ({
      name: suggestion.name,
      index: index
    }))
    .find(({ name }) => suggestion.name === name)
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
      highlightedOption.value = null
      selectSibilingElement(0)
    }

    firstSelectableIndex.value = filteredSuggestions.value.findIndex((s) => s.name !== null)

    const selectedFilteredSuggestion = filteredSuggestions.value.filter(
      (s: Suggestion) => s.name === selectedOption.value && selectedOption.value !== null
    )
    if (selectedFilteredSuggestion.length === 1 && newFilterString.value === '') {
      highlightedOption.value = selectedFilteredSuggestion[0] || null
    } else {
      highlightedOption.value = filteredSuggestions.value[0] || null
    }
  },
  { deep: 2 }
)

function onKeyEnter(event: InputEvent): void {
  event.stopPropagation()
  if (highlightedOption.value === null) {
    selectSibilingElement(0)
  }
  selectSuggestion(highlightedOption.value)

  if (highlightedOption.value?.name === selectedOption.value) {
    emit('request-close-suggestions')
  }
}

function selectSuggestion(suggestion: Suggestion | null) {
  if (suggestion?.name === null) {
    selectSibilingElement(0)
    selectedOption.value = highlightedOption.value?.name || null
    return
  }
  selectedOption.value = suggestion?.name || null
}

function selectSibilingElement(direction: number) {
  const selectableElements = filteredSuggestions.value.filter(
    (suggestion) => suggestion.name !== null
  )

  if (!selectableElements.length) {
    highlightedOption.value = null
    return
  }

  const currentIndex = findSuggestionAsIndex(selectableElements, highlightedOption.value) ?? 0

  highlightedOption.value =
    selectableElements[wrap(currentIndex + direction, filteredSuggestions.value.length)] || null
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
      selectSuggestion(filteredSuggestions.value[index]!)
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
    @keydown.tab.prevent="onKeyEnter"
    @keydown.escape.prevent="emit('request-close-suggestions')"
    @keydown.down.prevent="selectNextElement"
    @keydown.up.prevent="selectPreviousElement"
  >
    <span :class="{ hidden: !showFilter, input: true }">
      <input
        ref="suggestionInputRef"
        v-model="filterString"
        :aria-label="t('filter-aria-label', 'filter')"
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
        :class="{
          selectable: suggestion.name !== null,
          selected: isSuggestionHighlighted(suggestion, index)
        }"
        @click="selectSuggestion(suggestion)"
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
  max-width: 512px;
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
    color: var(--font-color-dimmed);

    &:focus {
      outline: none;
    }

    &.selectable {
      cursor: pointer;
      color: var(--font-color);
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
