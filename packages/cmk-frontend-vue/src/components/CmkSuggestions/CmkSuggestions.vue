<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkHtml from '@/components/CmkHtml.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { ErrorResponse, Response, type Suggestion } from './suggestions'

const { _t } = usei18n()

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
}

export type Suggestions = SuggestionsFixed | SuggestionsFiltered | SuggestionsCallbackFiltered

const {
  selectedSuggestion,
  suggestions,
  role,
  noResultsHint = ''
} = defineProps<{
  selectedSuggestion: string | null
  suggestions: Suggestions
  role: 'suggestion' | 'option'
  noResultsHint?: string
}>()

const showFilter = computed<boolean>(() => {
  return suggestions.type === 'filtered' || suggestions.type === 'callback-filtered'
})

const emit = defineEmits<{
  'select-suggestion': [Suggestion | null]
  'request-close-suggestions': []
  blur: []
}>()

const error = ref<string>('')
const suggestionRefs = useTemplateRef('suggestionRefs')
const filterString = ref<string>('')
const suggestionInputRef = ref<HTMLInputElement | null>(null)

const filteredSuggestions = ref<Array<Suggestion>>([])
const activeSuggestion: Ref<Suggestion | null> = ref(null) // null means no suggestion is highlighted, (no suggestions are selectable)
const isSelectedSuggestionSetAsFilter = ref(false)

function scrollCurrentActiveIntoView(): void {
  if (suggestionRefs.value === null) {
    return
  }
  const index = findSuggestionAsIndex(filteredSuggestions.value, activeSuggestion.value)
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
  () => ({
    newSuggestions: suggestions,
    newFilterString: filterString,
    newSelectedSuggestion: selectedSuggestion
  }),
  async ({ newSuggestions, newFilterString, newSelectedSuggestion }) => {
    const result = await getSuggestions(newSuggestions, newFilterString.value)

    if (result instanceof ErrorResponse) {
      error.value = result.error
    } else {
      error.value = ''
      filteredSuggestions.value = result.choices
      const foundSuggestion = newSelectedSuggestion
        ? filteredSuggestions.value.find((s) => s.name === newSelectedSuggestion)
        : null

      if (newSelectedSuggestion !== null && !isSelectedSuggestionSetAsFilter.value) {
        filterString.value = foundSuggestion?.title ?? newSelectedSuggestion
        isSelectedSuggestionSetAsFilter.value = true
      }
      if (foundSuggestion) {
        activeSuggestion.value = foundSuggestion
      } else {
        activeSuggestion.value = null
        setSiblingOrFirstActive(0)
      }
    }
  },
  { deep: 2 }
)

function onKeyEnter(event: InputEvent): void {
  event.stopPropagation()
  if (activeSuggestion.value === null) {
    return
  }
  selectSuggestion(activeSuggestion.value)
}

function selectSuggestion(suggestion: Suggestion | null) {
  if (suggestion && suggestion.name === null) {
    // do not select non-selectable elements
    return
  }
  if (suggestion && suggestion.name === selectedSuggestion) {
    emit('request-close-suggestions')
    return
  }
  emit('select-suggestion', suggestion)
}

function setSiblingOrFirstActive(offset: number) {
  const selectableElements = filteredSuggestions.value.filter(
    (suggestion) => suggestion.name !== null
  )

  if (!selectableElements.length) {
    activeSuggestion.value = null
    return
  }

  const currentActiveIndex = findSuggestionAsIndex(selectableElements, activeSuggestion.value) ?? 0

  activeSuggestion.value =
    selectableElements[wrap(currentActiveIndex + offset, selectableElements.length)] || null
}

function wrap(index: number, length: number): number {
  return (index + length) % length
}

function selectNextElement() {
  setSiblingOrFirstActive(+1)
  scrollCurrentActiveIntoView()
}
function selectPreviousElement() {
  setSiblingOrFirstActive(-1)
  scrollCurrentActiveIntoView()
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
        :aria-label="_t('filter')"
        type="text"
        @blur="inputLostFocus"
        @keydown.escape.prevent="emit('blur')"
      />
    </span>
    <CmkScrollContainer :max-height="'200px'">
      <li v-if="error" class="cmk-suggestions--error"><CmkHtml :html="error" /></li>
      <!-- eslint-disable vue/valid-v-for vue/require-v-for-key since the index in suggestionRefs does not get correctly updated when using the suggestion name as key -->
      <li
        v-for="suggestion in filteredSuggestions"
        ref="suggestionRefs"
        tabindex="-1"
        :role="role"
        :class="{
          selectable: suggestion.name !== null,
          selected: suggestion.name === activeSuggestion?.name
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
  z-index: var(--z-index-dropdown-offset);
  color: var(--font-color);
  background-color: var(--default-form-element-bg-color);
  border: 1px solid var(--ux-theme-6);
  box-sizing: border-box;
  border-radius: 0;
  min-width: 100%;
  max-width: 512px;
  margin: 0;
  padding: 0;
  list-style-type: none;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  span.input {
    display: flex;
    padding: 4px;

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
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

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.selectable {
      cursor: pointer;
      color: var(--font-color);

      /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
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
  width: fit-content;
}
</style>
