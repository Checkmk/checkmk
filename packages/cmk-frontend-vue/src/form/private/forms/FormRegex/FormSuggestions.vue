<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { Autocompleter, Regex } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import { ErrorResponse, Response, type Suggestion } from '@/components/CmkSuggestions/suggestions'

import { fetchSuggestions } from '@/form/private/FormAutocompleter/autocompleter'

import FormSuggestionsList from './FormSuggestionsList.vue'

const emit = defineEmits<{
  'request-close-suggestions': []
  blur: []
}>()
const { _t } = usei18n()
const { type, spec } = defineProps<{
  type: string
  spec: Regex
}>()
const suggestionsMode = ref<'preview' | 'all'>('preview')
const rootRef = ref<HTMLElement | null>(null)
const suggestionListRef = ref<InstanceType<typeof FormSuggestionsList> | null>(null)

const data = defineModel<string>('data', { required: true, default: '' })

const hostNameAutocompleter = computed<Autocompleter>(() => ({
  fetch_method: spec.autocompleter.fetch_method,
  data: {
    ...spec.autocompleter.data,
    context: { input_type: type }
  }
}))

async function suggestionCallback(query: string): Promise<ErrorResponse | Response> {
  if (hostNameAutocompleter.value === undefined) {
    return new ErrorResponse('internal: hostNameAutocompleter undefined')
  }
  const newValue = await fetchSuggestions(hostNameAutocompleter.value, query)
  if (newValue instanceof ErrorResponse) {
    return newValue
  }

  const result: Array<Suggestion> = newValue.choices.filter(
    (element: Suggestion) =>
      element.name === null || (element.name.length > 0 && element.title.length > 0)
  )

  return new Response(result)
}

defineExpose({
  selectNextElement: () => suggestionListRef.value?.selectNextElement(),
  selectPreviousElement: () => suggestionListRef.value?.selectPreviousElement(),
  selectHighlightedSuggestion: () => suggestionListRef.value?.selectHighlightedSuggestion(),
  rootRef
})
</script>

<template>
  <ul class="form-suggestions__text">
    <CmkScrollContainer v-if="type === 'text'" type="outer" :max-height="'200px'">
      <FormSuggestionsList
        ref="suggestionListRef"
        v-model:data="data"
        v-model:suggestions-mode="suggestionsMode"
        :type="'text'"
        :spec="spec"
        :role="'suggestion'"
        :suggestions="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
        @request-close-suggestions="emit('request-close-suggestions')"
      />
    </CmkScrollContainer>
  </ul>
  <ul class="form-suggestions__regex">
    <CmkScrollContainer
      v-if="suggestionsMode === 'all' && type === 'regex'"
      type="outer"
      :max-height="'200px'"
    >
      <FormSuggestionsList
        v-model:data="data"
        :suggestions-mode="suggestionsMode"
        :type="'regex'"
        :spec="spec"
        :role="'list'"
        :suggestions="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
        @request-close-suggestions="emit('request-close-suggestions')"
      />
    </CmkScrollContainer>
    <button
      v-show="suggestionsMode === 'all' && type === 'regex'"
      class="form-suggestions__button"
      type="button"
      @click.stop="suggestionsMode = 'preview'"
    >
      {{ _t('show preview') }}
    </button>

    <FormSuggestionsList
      v-if="suggestionsMode === 'preview' && type === 'regex'"
      v-model:data="data"
      :suggestions-mode="suggestionsMode"
      :type="'regex'"
      :spec="spec"
      :role="'list'"
      :suggestions="{ type: 'callback-filtered', querySuggestions: suggestionCallback }"
      @request-close-suggestions="emit('request-close-suggestions')"
    />
    <button
      v-show="suggestionsMode === 'preview' && type === 'regex'"
      class="form-suggestions__button"
      type="button"
      @click.stop="suggestionsMode = 'all'"
    >
      {{ _t('show all') }}
    </button>
  </ul>
</template>

<style scoped>
.form-suggestions__button {
  display: block;
  position: sticky;
  bottom: 0;
  background: var(--ux-theme-5);
  width: 100%;
  left: 0;
  border: none;
  border-radius: 0;
  color: var(--font-color-dimmed);
  cursor: pointer;
  font: inherit;
  margin: 0;
  padding: 6px 0 !important;
  text-align: center;
  text-decoration: underline;
}

.form-suggestions__regex {
  position: absolute;
  background-color: var(--ux-theme-3);
  border: 2px solid var(--ux-theme-5);
  border-top: 4px solid var(--ux-theme-5);
  border-radius: 2px;
  border-top-left-radius: 0;
  margin: 0;
  padding: 0;
  list-style-type: none;
  transform: translateX(-86.5px);
  width: 265px;
  z-index: var(--z-index-dropdown-offset);
}

.form-suggestions__text {
  position: absolute;
  background-color: var(--ux-theme-3);
  border: 2px solid var(--ux-theme-5);
  border-top: 4px solid var(--ux-theme-5);
  border-radius: 2px;
  border-top-left-radius: 0;
  margin: 0;
  padding: 0;
  list-style-type: none;
  transform: translateX(-86.5px);
  width: 265px;
  z-index: var(--z-index-dropdown-offset);
}
</style>
