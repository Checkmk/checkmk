<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import {
  ErrorResponse,
  Response,
  type Section,
  type Suggestion,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import FormValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { ref, watch } from 'vue'

import type { ValidationMessages } from '@/form'

import FormAttributeFilter from './attribute-filter/FormAttributeFilter.vue'
import { SUPPORTED_OPERATORS } from './attribute-filter/types'
import type { AttributeFilterModel, Condition, Operator } from './attribute-filter/types'
import {
  VALUE_IDENTS,
  buildAutocompleteContext,
  fromAttributeFilter,
  toAttributeFilter
} from './attributeFilterAdapter'
import { useAttributeKeySuggestions } from './attributeKeySuggestions'

const props = withDefaults(
  defineProps<{
    label: TranslatedString
    metricName?: string | null
    staticResourceAttributeKeys?: string[] | null
    indent?: boolean
    operators?: Operator[]
    allowOr?: boolean
  }>(),
  {
    metricName: null,
    staticResourceAttributeKeys: null,
    indent: false,
    operators: () => SUPPORTED_OPERATORS,
    allowOr: true
  }
)

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })

const attributeFilter = defineModel<AttributeFilter | undefined>('attributeFilter', {
  default: undefined
})

// The flat pill model is the UI's single source of truth.
const filterModel = ref<AttributeFilterModel>(
  attributeFilter.value ? fromAttributeFilter(attributeFilter.value, () => randomId()) : []
)
// Populate the filter up front so an unedited form still submits it (watch fires only on change).
attributeFilter.value = toAttributeFilter(filterModel.value)
const validationMessages = ref<string[]>([])

const {
  querySuggestions,
  resolveAttributeKind,
  cachedSuggestions,
  suggestionRevision,
  clearCache: clearSuggestionCache
} = useAttributeKeySuggestions((excludeId) =>
  buildAutocompleteContext(filterModel.value, {
    metricName: props.metricName,
    staticResourceAttributeKeys: props.staticResourceAttributeKeys,
    excludeId
  })
)

function queryKeySuggestions(condition: Condition, query: string): Promise<Response> {
  return querySuggestions(query, condition.id)
}

watch(
  filterModel,
  (model) => {
    attributeFilter.value = toAttributeFilter(model)
  },
  { deep: true }
)

watch(
  () => props.metricName,
  () => {
    filterModel.value = []
    // Suggestions are scoped to the metric, so the previous metric's cache is stale.
    clearSuggestionCache()
  }
)

immediateWatch(
  () => backendValidation.value,
  (newValidation: ValidationMessages | undefined) => {
    validationMessages.value = (newValidation ?? []).map((message) => message.message)
  }
)

// The backend echoes the typed text back as a (query, query) choice; drop it since we
// offer our own free-text entry, along with any incomplete suggestion.
function suggestionsWithoutEcho(
  choices: Array<Suggestion> | Array<Section>,
  query: string
): Suggestion[] {
  return flattenSuggestions(choices).filter(
    (suggestion) =>
      suggestion.name !== query &&
      (suggestion.name === null || (suggestion.name.length > 0 && suggestion.title.length > 0))
  )
}

async function queryValueSuggestions(condition: Condition, query: string): Promise<Response> {
  // Always offer the typed text as a free-text entry, even when the backend cannot help.
  const userEntry: Suggestion[] = query ? [{ name: query, title: untranslated(query) }] : []
  if (condition.attributeKind === null || !condition.key) {
    return new Response(userEntry)
  }
  // Scope suggestions to the edited pill's AND group; sibling OR disjuncts must not narrow them.
  const editedGroup = filterModel.value.find((group) =>
    group.conditions.some((candidate) => candidate.id === condition.id)
  )
  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: VALUE_IDENTS[condition.attributeKind],
      params: {
        context: buildAutocompleteContext(editedGroup ? [editedGroup] : [], {
          metricName: props.metricName,
          staticResourceAttributeKeys: props.staticResourceAttributeKeys,
          attributeKey: condition.key,
          excludeId: condition.id
        })
      }
    }
  }
  const response = cachedSuggestions(autocompleter, query)
  if (!response || response instanceof ErrorResponse) {
    return new Response(userEntry)
  }
  return new Response([...userEntry, ...suggestionsWithoutEcho(response.choices, query)])
}

function clearAttributeSelection(): void {
  filterModel.value = []
}

function hasInvalidAttributes(): boolean {
  return filterModel.value
    .flatMap((group) => group.conditions)
    .some(
      (condition) =>
        condition.key && condition.operator === 'equals' && condition.value.trim() === ''
    )
}

function getValidationMessages(): ValidationMessages {
  if (!hasInvalidAttributes()) {
    return []
  }
  return [
    {
      message: 'Attribute values cannot be empty.',
      location: ['attribute_filter'],
      replacement_value: attributeFilter.value ?? { type: 'and', conjuncts: [] }
    }
  ]
}

defineExpose({ clearAttributeSelection, hasInvalidAttributes, getValidationMessages })
</script>

<template>
  <div>
    <FormValidation :validation="validationMessages" />
    <component :is="props.indent ? CmkIndent : 'div'">
      <FormAttributeFilter
        v-model="filterModel"
        :allow-or="props.allowOr"
        :operators="props.operators"
        :query-suggestions="queryKeySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        :suggestion-revision="suggestionRevision"
        :resolve-attribute-kind="resolveAttributeKind"
        :aria-label="props.label"
      />
    </component>
  </div>
</template>
