<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, h, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { immediateWatch } from '@/lib/watch'

import CmkHtml from '@/components/CmkHtml.vue'
import type { Response } from '@/components/CmkSuggestions/suggestions'
import { ErrorResponse, type Suggestion } from '@/components/CmkSuggestions/suggestions'

type SuggestionsCallbackFiltered = {
  type: 'callback-filtered'
  querySuggestions: (query: string) => Promise<ErrorResponse | Response>
  getTitle?: (name: string) => Promise<ErrorResponse | TranslatedString>
}

const emit = defineEmits<{
  'request-close-suggestions': []
}>()

const { type, suggestionsMode, spec, role, suggestions } = defineProps<{
  type: string
  suggestionsMode: 'preview' | 'all'
  role: string
  spec: Regex
  suggestions: SuggestionsCallbackFiltered
}>()

const { _t } = usei18n()

const data = defineModel<string>('data', { required: true, default: '' })

const highlightedOption = ref<Suggestion | null>(null)
const suggestionRefs = useTemplateRef('suggestionRefs')
const firstSelectableIndex = ref(0)
const filteredSuggestions = ref<Array<Suggestion>>([])
const error = ref('error')
const filteredSuggestionsCount = computed(() => filteredSuggestions.value.length)

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
  suggestions: SuggestionsCallbackFiltered,
  query: string
): Promise<Response | ErrorResponse> {
  return await suggestions.querySuggestions(query)
}
immediateWatch(
  () => ({ newOptions: suggestions, newSelectedOption: data.value }),
  async ({ newOptions, newSelectedOption }) => {
    async function getInputValue(): Promise<string> {
      if (newSelectedOption === null) {
        return ''
      }
      if ('getTitle' in newOptions && typeof newOptions.getTitle === 'function') {
        const result = await newOptions.getTitle(newSelectedOption)
        if (result instanceof ErrorResponse) {
          console.error('CmkDropdown: internal: getTitle returned an error:', result.error)
          return `id: ${newSelectedOption}`
        }
        return result
      }
      return newSelectedOption
    }
    const val = await getInputValue()
    data.value = val
  },
  { deep: 2 }
)

immediateWatch(
  () => ({ newSuggestions: suggestions, newFilterString: data.value }),
  async ({ newSuggestions, newFilterString }) => {
    const result = await getSuggestions(newSuggestions, newFilterString)
    if (newFilterString === '') {
      error.value = ''
      filteredSuggestions.value = []
      highlightedOption.value = null
      return
    }
    if (result instanceof ErrorResponse) {
      error.value = result.error
    } else {
      error.value = ''
      filteredSuggestions.value = result.choices
      highlightedOption.value = null
      selectSiblingElement(0)
    }

    firstSelectableIndex.value = filteredSuggestions.value.findIndex((s) => s.name !== null)
    const selectedFilteredSuggestion = filteredSuggestions.value.filter(
      (s: Suggestion) => s.name === data.value && data.value !== null
    )
    if (selectedFilteredSuggestion.length === 1 && newFilterString === '') {
      highlightedOption.value = selectedFilteredSuggestion[0] || null
    } else {
      highlightedOption.value = filteredSuggestions.value[0] || null
    }
  },
  { deep: 2 }
)

function wrap(index: number, length: number): number {
  return (index + length) % length
}
const suggestionInputRef = ref<HTMLInputElement | null>(null)

async function focus(): Promise<void> {
  suggestionInputRef.value?.focus()
}

function selectSiblingElement(direction: number) {
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

function selectSuggestion(suggestion: Suggestion | null) {
  if (suggestion?.name === null) {
    selectSiblingElement(0)
    data.value = highlightedOption.value?.name || ''

    return
  }
  data.value = suggestion?.name || ''
}

function selectNextElement() {
  selectSiblingElement(+1)
  scrollCurrentlySelectedIntoView()
}
function selectPreviousElement() {
  selectSiblingElement(-1)
  scrollCurrentlySelectedIntoView()
}

function selectHighlightedSuggestion() {
  selectSuggestion(highlightedOption.value)
  emit('request-close-suggestions')
}

//Only used for POC, will be done in BE later
function getHighlightedParts(type: string, title: string, query: string) {
  if (type === 'regex') {
    return getHighlightedPartsRegex(title, query)
  }
  return getHighlightedPartsText(title, query)
}
//Only used for POC, will be done in BE later
function getHighlightedPartsText(title: string, query: string) {
  if (!query) {
    return h('span', title)
  }
  const lowerTitle = title.toLowerCase()
  const lowerQuery = query.toLowerCase()
  if (!lowerTitle.includes(lowerQuery)) {
    return h('span', title)
  }

  const parts = []
  let lastIndex = 0
  let index

  while ((index = lowerTitle.indexOf(lowerQuery, lastIndex)) !== -1) {
    if (index > lastIndex) {
      parts.push(h('span', title.slice(lastIndex, index)))
    }
    parts.push(
      h(
        'span',
        { class: 'form-suggestions-list__highlight' },
        title.slice(index, index + query.length)
      )
    )
    lastIndex = index + query.length
  }
  if (lastIndex < title.length) {
    parts.push(h('span', title.slice(lastIndex)))
  }
  return h('span', parts)
}
//Only used for POC, will be done in BE later
function getHighlightedPartsRegex(title: string, query: string) {
  if (!query) {
    return h('span', title)
  }

  let regex: RegExp
  try {
    regex = new RegExp(query, 'gi')
  } catch {
    return h('span', title)
  }

  const parts = []
  let lastIndex = 0
  let match

  while ((match = regex.exec(title)) !== null) {
    if (match.index > lastIndex) {
      parts.push(h('span', title.slice(lastIndex, match.index)))
    }
    parts.push(h('span', { class: 'form-suggestions-list__highlight' }, match[0]))
    lastIndex = match.index + match[0].length
    if (regex.lastIndex === match.index) {
      regex.lastIndex++
    }
  }
  if (lastIndex < title.length) {
    parts.push(h('span', title.slice(lastIndex)))
  }
  return h('span', parts)
}

defineExpose({
  focus,
  selectNextElement,
  selectPreviousElement,
  selectSiblingElement,
  selectHighlightedSuggestion,
  filteredSuggestionsCount
})
</script>
<template>
  <li
    v-if="type === 'regex' && suggestionsMode === 'preview' && filteredSuggestions.length > 0"
    class="form-suggestions-list__preview-text-li form-suggestions-list__li"
  >
    {{ _t('Preview of matches:') }}
  </li>
  <li v-if="error" class="form-suggestions-list__li">
    <CmkHtml :html="error" />
  </li>
  <!-- eslint-disable vue/valid-v-for vue/require-v-for-key -->
  <li
    v-for="(suggestion, index) in type === 'regex' && suggestionsMode === 'preview'
      ? filteredSuggestions.slice(0, 5)
      : filteredSuggestions"
    ref="suggestionRefs"
    tabindex="-1"
    :role="role"
    :class="[
      'form-suggestions-list__li',
      {
        selectable: type === 'text' && suggestion.name !== null,
        selected: isSuggestionHighlighted(suggestion, index)
      }
    ]"
    @click="
      type === 'text'
        ? (selectSuggestion(suggestion), emit('request-close-suggestions'))
        : undefined
    "
  >
    <component :is="getHighlightedParts(type, suggestion.title, data)" />
  </li>

  <li
    v-if="filteredSuggestions.length === 0 && spec.no_results_hint !== ''"
    class="form-suggestions-list__li"
  >
    {{ spec.no_results_hint }}
  </li>
</template>
<style scoped>
.form-suggestions-list__highlight {
  color: var(--color-white-100);
  font-weight: var(--font-weight-bold);
}

.form-suggestions-list__preview-text-li {
  padding: 6px;
  padding-left: 85px !important;
}

.form-suggestions-list__li {
  padding: 6px;
  padding-left: 100px;
  cursor: default;
  color: var(--font-color-dimmed);

  &:focus {
    outline: none;
  }

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.selectable {
    cursor: pointer;
    color: var(--font-color-dimmed);

    /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
    &.selected {
      color: var(--color-white-100);
      background-color: var(--color-white-10);
    }

    &:hover {
      color: var(--color-white-100);
    }
  }
}
</style>
