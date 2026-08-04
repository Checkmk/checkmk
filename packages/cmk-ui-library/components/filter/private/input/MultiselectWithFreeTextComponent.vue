<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
One input for a filter whose values are open-ended: what you type is the value,
and the autocompleter's suggestions are offered below it rather than replacing
it. So a value the list knows is picked, and one it cannot know is simply typed
- the shape FormRegex uses for "Host name (regex)".

The input owns the value, which is what makes free text work at all: a picker
that owns it has nowhere to put a string matching no suggestion. Committed
values accumulate as chips and are written to the filter's single variable,
joined by the declared separator, and match as alternatives.
-->
<script setup lang="ts">
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import {
  ErrorResponse,
  type Suggestion,
  Response as SuggestionsResponse
} from 'cmk-ui-library/components/CmkSuggestions'
import type { QuerySuggestionsFn } from 'cmk-ui-library/components/CmkSuggestions/types'
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref, toRaw, watch } from 'vue'

import type { MultiselectWithFreeTextConfig } from '../../types.ts'
import type { ComponentEmits, FilterComponentProps } from './types.ts'

const { _t } = usei18n()

const props = defineProps<FilterComponentProps<MultiselectWithFreeTextConfig>>()
const emit = defineEmits<ComponentEmits>()

const currentValue = ref(props.configuredValues?.[props.component.id] ?? '')

// The dropdown's selection, which is only ever a value on its way into the
// list below - it is cleared again as soon as it has been taken.
const picked = ref<string | null>(null)

if (props.configuredValues === null) {
  emit('update-component-values', props.component.id, { [props.component.id]: currentValue.value })
}

watch(
  () => props.configuredValues?.[props.component.id],
  (value) => {
    if (value !== undefined && value !== currentValue.value) {
      currentValue.value = value
    }
  }
)

watch(currentValue, (value) => {
  emit('update-component-values', props.component.id, { [props.component.id]: value })
})

/** The chosen values, in the order they were added. */
const values = computed(() =>
  currentValue.value
    .split(props.component.separator)
    .map((entry) => entry.trim())
    .filter((entry) => entry !== '')
)

function writeValues(next: string[]): void {
  currentValue.value = next.join(
    props.component.separator === ',' ? ', ' : props.component.separator
  )
}

function addValue(value: string): void {
  // A value carrying the separator is really several, so honour that rather
  // than creating one entry that can never match.
  const entries = value
    .split(props.component.separator)
    .map((entry) => entry.trim())
    .filter((entry) => entry !== '')
  const next = [...values.value]
  for (const entry of entries) {
    if (!next.includes(entry)) {
      next.push(entry)
    }
  }
  writeValues(next)
}

function removeValue(value: string): void {
  writeValues(values.value.filter((entry) => entry !== value))
}

watch(picked, (value) => {
  if (value === null || value === '') {
    return
  }
  addValue(value)
  // Clear it so the same value can be chosen again after removal, and so the
  // dropdown never reads as holding a value of its own.
  picked.value = null
})

/**
 * The autocompleter's suggestions, with whatever is typed offered as an entry
 * of its own.
 *
 * That echo is what makes a value the list cannot know selectable at all: the
 * dropdown only ever commits something it offered, so the free text has to be
 * among the offers. It is left out when it would duplicate a known name, so
 * picking never resolves to the echo instead of the real entry.
 */
const querySuggestions: QuerySuggestionsFn = async (query) => {
  const response = await fetchSuggestions(autocompleter, query)
  if (response instanceof ErrorResponse) {
    return response
  }
  const known = (response.choices as Suggestion[]).filter(notAlreadyChosen)
  const typed = query.trim()
  const echo: Suggestion[] =
    typed !== '' && !known.some((suggestion) => suggestion.name === typed)
      ? [{ name: typed, title: untranslated(typed) }]
      : []
  return new SuggestionsResponse([...echo, ...known])
}

// The hint comes from the filter definition, so it is already translated
// server-side; the default is translated here.
const pickHint = computed(() =>
  props.component.pick_hint === undefined || props.component.pick_hint === ''
    ? _t('Select a value...')
    : untranslated(props.component.pick_hint)
)

const decodedLabel = computed(() => props.component.label?.replace(/&nbsp;/g, '\u00A0') ?? '')

// A plain copy, not the prop itself: the definition reaches us as a reactive
// proxy, and the fetch layer structuredClone()s what it is given - which throws
// DataCloneError on a proxy, before any request goes out.
// A value already chosen is not worth offering again - picking it would be a
// no-op, and it only crowds out the ones still to be had.
function notAlreadyChosen(suggestion: Suggestion): boolean {
  return suggestion.name === null || !values.value.includes(suggestion.name)
}

const autocompleter: Autocompleter = {
  fetch_method: 'ajax_vs_autocomplete',
  data: structuredClone(toRaw(props.component.autocompleter))
}
</script>

<template>
  <div class="cmk-multiselect-with-free-text-component">
    <CmkLabel v-if="component.label" :for="component.id">
      {{ decodedLabel }}
    </CmkLabel>
    <CmkDropdown
      v-model="picked"
      :options="{ type: 'callback-filtered', querySuggestions }"
      :input-hint="pickHint"
      :label="pickHint"
      :no-results-hint="_t('No matching values')"
      :width="'fill'"
      floating
    />

    <div v-if="values.length" class="cmk-multiselect-with-free-text-component__values-header">
      <span>{{ _t('Any of') }}</span>
      <CmkHelpText
        :help="_t('A row matches when it matches any one of these values, not all of them.')"
        :aria-label="_t('How several values are combined')"
      />
    </div>

    <ul v-if="values.length" class="cmk-multiselect-with-free-text-component__values">
      <li v-for="value in values" :key="value">
        <CmkChip size="small" color="others" variant="outline" as-div>
          {{ value }}
          <template #end>
            <CmkIconButton
              name="close"
              size="xxsmall"
              :aria-label="_t('Remove %{value}', { value })"
              @click="removeValue(value)"
            />
          </template>
        </CmkChip>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cmk-multiselect-with-free-text-component {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  width: 100%;
}

.cmk-multiselect-with-free-text-component__values-header {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  opacity: 0.7;
}

.cmk-multiselect-with-free-text-component__values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
