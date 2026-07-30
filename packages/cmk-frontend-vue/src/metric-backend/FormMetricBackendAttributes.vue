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
import { fetchSuggestions } from 'cmk-ui-library/components/FormAutocompleter/autocompleter'
import FormValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { randomId } from 'cmk-ui-library/lib/randomId'
import { immediateWatch } from 'cmk-ui-library/lib/watch'
import { ref, watch } from 'vue'

import type { ValidationMessages } from '@/form'

import FormAttributeFilter from './attribute-filter/FormAttributeFilter.vue'
import { SUPPORTED_OPERATORS } from './attribute-filter/types'
import type {
  AttributeFilterModel,
  AttributeKind,
  Condition,
  Operator
} from './attribute-filter/types'
import {
  ATTRIBUTE_KIND_ORDER,
  type AttributeKindKey,
  KEY_IDENTS,
  VALUE_IDENTS,
  buildAutocompleteContext,
  fromAttributeFilter,
  toAttributeFilter
} from './attributeFilterAdapter'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    metricName?: string | null
    staticResourceAttributeKeys?: string[] | null
    indent?: boolean
    operators?: Operator[]
  }>(),
  {
    metricName: null,
    staticResourceAttributeKeys: null,
    indent: false,
    operators: () => SUPPORTED_OPERATORS
  }
)

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })

const attributeFilter = defineModel<AttributeFilter | undefined>('attributeFilter', {
  default: undefined
})

const SECTION_TITLES: Record<AttributeKindKey, TranslatedString> = {
  resource: _t('Resource'),
  scope: _t('Scope'),
  data_point: _t('Data point')
}

// The flat pill model is the UI's single source of truth.
const filterModel = ref<AttributeFilterModel>(
  attributeFilter.value ? fromAttributeFilter(attributeFilter.value, () => randomId()) : []
)
// Populate the filter up front so an unedited form still submits it (watch fires only on change).
attributeFilter.value = toAttributeFilter(filterModel.value)
// A key may be offered under more than one attribute kind, so record the set of
// kinds each suggested key belongs to (see `resolveAttributeKind`).
const keyKindCache = new Map<string, Set<AttributeKindKey>>()
const validationMessages = ref<string[]>([])

function cacheKeyKind(name: string, attributeKind: AttributeKindKey): void {
  const kinds = keyKindCache.get(name)
  if (kinds) {
    kinds.add(attributeKind)
  } else {
    keyKindCache.set(name, new Set([attributeKind]))
  }
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
  }
)

immediateWatch(
  () => backendValidation.value,
  (newValidation: ValidationMessages | undefined) => {
    validationMessages.value = (newValidation ?? []).map((message) => message.message)
  }
)

async function querySuggestions(query: string): Promise<Response | ErrorResponse> {
  // The three key autocompleters are independent, so fetch them concurrently.
  const responses = await Promise.all(
    ATTRIBUTE_KIND_ORDER.map((attributeKind) => {
      const autocompleter: Autocompleter = {
        fetch_method: 'rest_autocomplete',
        data: {
          ident: KEY_IDENTS[attributeKind],
          params: {
            context: buildAutocompleteContext(filterModel.value, {
              metricName: props.metricName,
              staticResourceAttributeKeys: props.staticResourceAttributeKeys
            })
          }
        }
      }
      return fetchSuggestions(autocompleter, query)
    })
  )
  const sections: Section[] = []
  ATTRIBUTE_KIND_ORDER.forEach((attributeKind, index) => {
    const response = responses[index]
    if (!response || response instanceof ErrorResponse) {
      return
    }
    // The backend echoes the typed text as a leading (query, query) choice; a real
    // key equal to the query is indistinguishable from the echo and is dropped too,
    // falling into the section-less user entry below (its type stays unresolved).
    const suggestions = flattenSuggestions(response.choices).filter(
      (s: Suggestion) =>
        s.name !== query && (s.name === null || (s.name.length > 0 && s.title.length > 0))
    )
    for (const suggestion of suggestions) {
      if (suggestion.name) {
        cacheKeyKind(suggestion.name, attributeKind)
      }
    }
    if (suggestions.length > 0) {
      sections.push({ title: SECTION_TITLES[attributeKind], suggestions })
    }
  })
  const userEntry: Section[] = query
    ? [{ title: untranslated(''), suggestions: [{ name: query, title: untranslated(query) }] }]
    : []
  return new Response([...userEntry, ...sections])
}

async function queryValueSuggestions(
  condition: Condition,
  query: string
): Promise<Response | ErrorResponse> {
  if (condition.attributeKind === null || !condition.key) {
    return new Response([])
  }
  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: VALUE_IDENTS[condition.attributeKind],
      params: {
        context: buildAutocompleteContext(filterModel.value, {
          metricName: props.metricName,
          staticResourceAttributeKeys: props.staticResourceAttributeKeys,
          attributeKey: condition.key,
          excludeId: condition.id
        })
      }
    }
  }
  const response = await fetchSuggestions(autocompleter, query)
  if (response instanceof ErrorResponse) {
    return response
  }
  return new Response(
    flattenSuggestions(response.choices).filter(
      (s: Suggestion) => s.name === null || (s.name.length > 0 && s.title.length > 0)
    )
  )
}

function resolveAttributeKind(key: string): AttributeKind {
  // A key offered under more than one attribute kind is ambiguous: leave it
  // unresolved so the attribute-kind dropdown opens for the user to choose.
  const kinds = keyKindCache.get(key)
  return kinds?.size === 1 ? [...kinds][0]! : null
}

function clearAttributeSelection(): void {
  filterModel.value = []
}

function hasInvalidAttributes(): boolean {
  return filterModel.value
    .flatMap((group) => group.conditions)
    .some(
      (condition) => condition.key && condition.operator === 'eq' && condition.value.trim() === ''
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
  <tr>
    <td class="metric-backend-form-metric-backend-attributes__label-cell">
      {{ _t('Attributes') }}
    </td>
    <td>
      <FormValidation :validation="validationMessages" />
      <component :is="props.indent ? CmkIndent : 'div'">
        <FormAttributeFilter
          v-model="filterModel"
          :allow-or="false"
          :operators="props.operators"
          :query-suggestions="querySuggestions"
          :query-value-suggestions="queryValueSuggestions"
          :resolve-attribute-kind="resolveAttributeKind"
          :aria-label="_t('Attributes')"
        />
      </component>
    </td>
  </tr>
</template>

<style scoped>
.metric-backend-form-metric-backend-attributes__label-cell {
  vertical-align: top;
}
</style>
