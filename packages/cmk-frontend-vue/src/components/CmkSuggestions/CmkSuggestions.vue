<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, nextTick, ref, useTemplateRef } from 'vue'

import usei18n from '@/lib/i18n'
import { useDebounceRef } from '@/lib/useDebounce'
import { immediateWatch } from '@/lib/watch'

import CmkHtml from '@/components/CmkHtml.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { ErrorResponse, type Suggestion, WarningResponse } from './suggestions'
import {
  NoSelection,
  type Section,
  type SuggestionValue,
  type Suggestions,
  isSectioned
} from './types'

type DisplaySection = Omit<Section, 'title'> & { title: Section['title'] | null }

const { _t } = usei18n()

const {
  selectedSuggestion,
  suggestions,
  role,
  noResultsHint = '',
  markSelected = false
} = defineProps<{
  selectedSuggestion: SuggestionValue
  suggestions: Suggestions
  role: 'suggestion' | 'option'
  noResultsHint?: string
  markSelected?: boolean
}>()

const showFilter = computed<boolean>(() => {
  return suggestions.type === 'filtered' || suggestions.type === 'callback-filtered'
})

const emit = defineEmits<{
  'select-suggestion': [Suggestion | null]
  'request-close-suggestions': []
  blur: []
}>()

defineSlots<{
  /** Per-option content; defaults to the suggestion's (match-highlighted) title. */
  option?: (props: { suggestion: Suggestion }) => unknown
}>()

const error = ref<string>('')
const warning = ref<string>('')
const suggestionRefs = useTemplateRef('suggestionRefs')
const filterString = ref<string>(
  suggestions.type === 'callback-filtered' ? selectedSuggestion.getTitle() || '' : ''
)
const suggestionInputRef = ref<HTMLInputElement | null>(null)

const displaySections = ref<Array<DisplaySection>>([])
const filteredSuggestions = computed<Array<Suggestion>>(() =>
  displaySections.value.flatMap((section) => section.suggestions)
)
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

function asSingleSection(suggestions: Array<Suggestion>): Array<DisplaySection> {
  return suggestions.length > 0 ? [{ title: null, suggestions }] : []
}

function buildSectionedDisplaySections(
  sections: Array<Section>,
  query: string,
  doFilter: boolean
): Array<DisplaySection> {
  const lowerCaseQuery = query.toLowerCase()
  const survivingSections = sections
    .map((section) => ({
      title: section.title,
      suggestions: doFilter
        ? section.suggestions.filter((s) => s.title.toLowerCase().includes(lowerCaseQuery))
        : section.suggestions
    }))
    .filter((section) => section.suggestions.length > 0)

  if (survivingSections.length <= 1) {
    return asSingleSection(survivingSections[0]?.suggestions ?? [])
  }

  return survivingSections.map((section) => ({
    title: section.title.trim() !== '' ? section.title : null,
    suggestions: section.suggestions
  }))
}

function buildDisplaySections(
  input: Array<Suggestion> | Array<Section>,
  query: string,
  doFilter: boolean
): Array<DisplaySection> {
  if (isSectioned(input)) {
    return buildSectionedDisplaySections(input, query, doFilter)
  }
  const lowerCaseQuery = query.toLowerCase()
  const items = doFilter
    ? input.filter((s) => s.title.toLowerCase().includes(lowerCaseQuery))
    : input
  return asSingleSection(items)
}

async function getDisplaySections(
  suggestions: Suggestions,
  query: string
): Promise<Array<DisplaySection> | ErrorResponse | WarningResponse> {
  switch (suggestions.type) {
    case 'filtered':
      return buildDisplaySections(suggestions.suggestions, query, true)
    case 'fixed':
      return buildDisplaySections(suggestions.suggestions, '', false)
    case 'callback-filtered': {
      const response = await suggestions.querySuggestions(query)
      if (response instanceof ErrorResponse || response instanceof WarningResponse) {
        return response
      }
      return buildDisplaySections(response.choices, '', false)
    }
  }
}

const debouncedFilterString = useDebounceRef(filterString)
const effectiveFilterString = () =>
  suggestions.type === 'callback-filtered' ? debouncedFilterString.value : filterString.value

type SplitParts = { before: string; match: string; after: string }

function splitOnQuery(text: string, query: string): SplitParts | null {
  const index = text.toLowerCase().indexOf(query.toLowerCase())
  if (index === -1) {
    return null
  }
  return {
    before: text.slice(0, index),
    match: text.slice(index, index + query.length),
    after: text.slice(index + query.length)
  }
}

type RowRender =
  | { kind: 'plain' }
  | { kind: 'title-match'; parts: SplitParts }
  | { kind: 'name-match'; nameParts: SplitParts }

function getRowRender(suggestion: Suggestion): RowRender {
  if (!showFilter.value) {
    return { kind: 'plain' }
  }
  const query = filterString.value
  if (query === '') {
    return { kind: 'plain' }
  }
  const titleParts = splitOnQuery(suggestion.title, query)
  if (titleParts !== null) {
    return { kind: 'title-match', parts: titleParts }
  }
  if (suggestion.name !== null) {
    const nameParts = splitOnQuery(suggestion.name, query)
    if (nameParts !== null) {
      return { kind: 'name-match', nameParts }
    }
  }
  return { kind: 'plain' }
}

async function handleSuggestionsUpdate(
  newSuggestions: Suggestions,
  query: string,
  newSelectedSuggestion: SuggestionValue
): Promise<void> {
  const result = await getDisplaySections(newSuggestions, query)

  if (result instanceof ErrorResponse) {
    error.value = result.error
    warning.value = ''
  } else if (result instanceof WarningResponse) {
    warning.value = result.warning
    error.value = ''
    displaySections.value = buildDisplaySections(result.choices, '', false)
    activeSuggestion.value = null
    setSiblingOrFirstActive(0)
  } else {
    error.value = ''
    warning.value = ''
    displaySections.value = result
    const foundSuggestion =
      newSelectedSuggestion instanceof NoSelection
        ? null
        : filteredSuggestions.value.find((s) => s.name === newSelectedSuggestion.getName())

    if (!(newSelectedSuggestion instanceof NoSelection) && !isSelectedSuggestionSetAsFilter.value) {
      if (newSuggestions.type === 'callback-filtered') {
        filterString.value = foundSuggestion?.title ?? newSelectedSuggestion.getName()

        isSelectedSuggestionSetAsFilter.value = true
      }
    }
    if (foundSuggestion && newSuggestions.type !== 'filtered') {
      activeSuggestion.value = foundSuggestion
    } else {
      activeSuggestion.value = null
      setSiblingOrFirstActive(0)
    }
  }
}

immediateWatch(
  () => ({
    newSuggestions: suggestions,
    newFilterString: effectiveFilterString(),
    newSelectedSuggestion: selectedSuggestion
  }),
  async ({ newSuggestions, newFilterString, newSelectedSuggestion }) => {
    await handleSuggestionsUpdate(newSuggestions, newFilterString, newSelectedSuggestion)
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
  if (suggestion && suggestion.name === selectedSuggestion.getName()) {
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
      <li v-if="warning" class="cmk-suggestions--warning"><CmkHtml :html="warning" /></li>
      <!-- eslint-disable vue/valid-v-for vue/require-v-for-key since the index in suggestionRefs does not get correctly updated when using the suggestion name as key -->
      <template v-for="(section, sIdx) in displaySections">
        <li
          v-if="section.title !== null"
          :key="`h-${sIdx}`"
          class="cmk-suggestions__section-header"
          role="heading"
          aria-level="3"
          :aria-label="section.title"
          tabindex="-1"
          @mousedown.prevent
        >
          {{ section.title }}
        </li>
        <li
          v-for="suggestion in section.suggestions"
          ref="suggestionRefs"
          tabindex="-1"
          :role="role"
          :aria-label="suggestion.title"
          :aria-selected="
            markSelected && suggestion.name !== null
              ? suggestion.name === selectedSuggestion.getName()
              : undefined
          "
          :class="{
            selectable: suggestion.name !== null,
            selected: suggestion.name === activeSuggestion?.name,
            'cmk-suggestions__item--in-section': section.title !== null,
            'cmk-suggestions__item--markable': markSelected
          }"
          @click="selectSuggestion(suggestion)"
        >
          <span class="cmk-suggestions__option">
            <slot name="option" :suggestion="suggestion">
              <template v-for="render in [getRowRender(suggestion)]">
                <template v-if="render.kind === 'title-match'">
                  <span>{{ render.parts.before }}</span
                  ><mark>{{ render.parts.match }}</mark
                  ><span>{{ render.parts.after }}</span>
                </template>
                <template v-else-if="render.kind === 'name-match'"
                  >{{ suggestion.title
                  }}<span class="cmk-suggestions__name-match">
                    ({{ render.nameParts.before }}<mark>{{ render.nameParts.match }}</mark
                    >{{ render.nameParts.after }})</span
                  >
                </template>
                <template v-else>{{ suggestion.title }}</template>
              </template>
            </slot>
          </span>
          <CmkIcon
            v-if="
              markSelected &&
              suggestion.name !== null &&
              suggestion.name === selectedSuggestion.getName()
            "
            name="checkmark-bare"
            size="small"
            aria-hidden="true"
            class="cmk-suggestions__selected-mark"
          />
        </li>
      </template>
      <!-- eslint-enable vue/valid-v-for vue/require-v-for-key -->
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
  background-color: var(--cmk-suggestions-background, var(--default-form-element-bg-color));
  border: 1px solid var(--cmk-suggestions-border-color, var(--ux-theme-6));
  box-sizing: border-box;
  border-radius: 0;
  width: fit-content;
  min-width: 100%;
  max-width: 512px;
  margin: 0;
  padding: 0;
  list-style-type: none;

  mark {
    background: transparent;
    color: var(--default-select-focus-color);
    font-weight: normal;
  }

  .cmk-suggestions__name-match {
    color: var(--font-color-dimmed);
    font-size: 0.9em;

    mark {
      color: var(--default-select-focus-color);
      font-weight: normal;
    }
  }

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
    field-sizing: content;
    box-sizing: border-box;
    min-width: 100%;
    max-width: 100%;
    padding: 10px 4px;
    margin: 0;
    color: var(--font-color);
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
        color: var(--cmk-suggestions-item-active-color, var(--default-select-focus-color));

        mark {
          font-weight: 700;
        }
      }

      &:hover {
        color: var(--cmk-suggestions-item-active-color, var(--default-select-hover-color));
        background-color: var(--cmk-suggestions-item-hover-background, transparent);
      }
    }

    &.cmk-suggestions__item--markable {
      display: flex;
      align-items: center;
    }

    /* Fill the row so a custom option (e.g. a tooltip trigger) can span the whole option,
       not just its text. Stays block-flow so the default title's match highlight is unaffected. */
    .cmk-suggestions__option {
      flex: 1;
      min-width: 0;
    }

    &.cmk-suggestions__item--in-section {
      padding-left: 18px;
    }

    .cmk-suggestions__selected-mark {
      flex-shrink: 0;
      margin-left: auto;
      padding-left: 8px;
    }
  }
}

.cmk-suggestions__section-header {
  position: sticky;
  top: 0;
  padding: 6px;
  background-color: var(--default-form-element-bg-color);
  color: var(--font-color);
  font-size: var(--font-size-small);
  font-weight: 700;
  cursor: default;
}

.cmk-suggestions--error,
.cmk-suggestions--warning {
  width: fit-content;
}

/* checkmark-bare ships a dark stroke with no dark-theme variant; tint it so it reads as
   --font-color on the dark theme. */
body[data-theme='modern-dark'] .cmk-suggestions__selected-mark {
  filter: brightness(0) invert(1);
}

.cmk-suggestions--error {
  background-color: var(--error-msg-bg-color);
}

.cmk-suggestions--warning {
  background-color: color-mix(in srgb, var(--color-yellow-50) 25%, transparent);
}
</style>
