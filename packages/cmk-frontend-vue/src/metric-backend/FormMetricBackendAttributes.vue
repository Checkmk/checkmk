<!--
Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { GraphLineQueryAttributes } from 'cmk-shared-typing/typescript/graph_designer'
import type { Autocompleter } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref, watch } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { immediateWatch } from '@/lib/watch'

import CmkIndent from '@/components/CmkIndent.vue'
import {
  ErrorResponse,
  Response,
  type Section,
  type Suggestion,
  flattenSuggestions
} from '@/components/CmkSuggestions'
import FormValidation from '@/components/user-input/CmkInlineValidation.vue'

import type { ValidationMessages } from '@/form'
import { fetchSuggestions } from '@/form/private/FormAutocompleter/autocompleter'

import FormAttributeFilter from './attribute-filter/FormAttributeFilter.vue'
import type {
  AttributeFilterModel,
  AttributeType,
  ConnectedCondition
} from './attribute-filter/types'
import {
  ATTRIBUTE_TYPE_ORDER,
  type AttributeTypeKey,
  KEY_IDENTS,
  type ThreeLists,
  VALUE_IDENTS,
  buildAutocompleteContext,
  fromModel,
  toModel
} from './attributeFilterAdapter'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    metricName?: string | null
    staticResourceAttributeKeys?: string[] | null
    indent?: boolean
  }>(),
  {
    metricName: null,
    staticResourceAttributeKeys: null,
    indent: false
  }
)

const backendValidation = defineModel<ValidationMessages>('backendValidation', { default: [] })

const resourceAttributes = defineModel<GraphLineQueryAttributes>('resourceAttributes', {
  default: []
})
const scopeAttributes = defineModel<GraphLineQueryAttributes>('scopeAttributes', {
  default: []
})
const dataPointAttributes = defineModel<GraphLineQueryAttributes>('dataPointAttributes', {
  default: []
})

const LOCATION_TO_TYPE: Record<string, AttributeTypeKey> = {
  resource_attributes: 'resource',
  scope_attributes: 'scope',
  data_point_attributes: 'datapoint'
}

const SECTION_TITLES: Record<AttributeTypeKey, TranslatedString> = {
  resource: _t('Resource'),
  scope: _t('Scope'),
  datapoint: _t('Data point')
}

// The flat pill model is the single source of truth; the three list models are
// kept in sync from it.
const filterModel = ref<AttributeFilterModel>(
  toModel(
    {
      resource: resourceAttributes.value,
      scope: scopeAttributes.value,
      datapoint: dataPointAttributes.value
    },
    () => crypto.randomUUID()
  )
)
// A key may be offered under more than one attribute type, so record the set of
// types each suggested key belongs to (see `resolveAttributeType`).
const keyTypeCache = new Map<string, Set<AttributeTypeKey>>()
const validationMessages = ref<string[]>([])

function cacheKeyType(name: string, attributeType: AttributeTypeKey): void {
  const types = keyTypeCache.get(name)
  if (types) {
    types.add(attributeType)
  } else {
    keyTypeCache.set(name, new Set([attributeType]))
  }
}

function attributesEqual(a: GraphLineQueryAttributes, b: GraphLineQueryAttributes): boolean {
  return (
    a.length === b.length &&
    a.every((attr, i) => attr.key === b[i]!.key && attr.value === b[i]!.value)
  )
}

// Only reassign a list model when its derived content actually changed, so an
// in-progress (key-less) pill or an unrelated edit does not churn the parent
// models with fresh array references on every keystroke.
watch(
  filterModel,
  (model) => {
    const lists = fromModel(model)
    if (!attributesEqual(lists.resource, resourceAttributes.value)) {
      resourceAttributes.value = lists.resource
    }
    if (!attributesEqual(lists.scope, scopeAttributes.value)) {
      scopeAttributes.value = lists.scope
    }
    if (!attributesEqual(lists.datapoint, dataPointAttributes.value)) {
      dataPointAttributes.value = lists.datapoint
    }
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
    validationMessages.value = []
    if (!newValidation || newValidation.length === 0) {
      return
    }
    const lists: ThreeLists = fromModel(filterModel.value)
    newValidation.forEach((message) => {
      validationMessages.value.push(message.message)
      const attributeType = LOCATION_TO_TYPE[message.location[0] ?? '']
      if (attributeType !== undefined) {
        lists[attributeType] = message.replacement_value as GraphLineQueryAttributes
      }
    })
    filterModel.value = toModel(lists, () => crypto.randomUUID())
  }
)

async function querySuggestions(query: string): Promise<Response | ErrorResponse> {
  // The three key autocompleters are independent, so fetch them concurrently.
  const responses = await Promise.all(
    ATTRIBUTE_TYPE_ORDER.map((attributeType) => {
      const autocompleter: Autocompleter = {
        fetch_method: 'rest_autocomplete',
        data: {
          ident: KEY_IDENTS[attributeType],
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
  ATTRIBUTE_TYPE_ORDER.forEach((attributeType, index) => {
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
        cacheKeyType(suggestion.name, attributeType)
      }
    }
    if (suggestions.length > 0) {
      sections.push({ title: SECTION_TITLES[attributeType], suggestions })
    }
  })
  const userEntry: Section[] = query
    ? [{ title: untranslated(''), suggestions: [{ name: query, title: untranslated(query) }] }]
    : []
  return new Response([...userEntry, ...sections])
}

async function queryValueSuggestions(
  condition: ConnectedCondition,
  query: string
): Promise<Response | ErrorResponse> {
  if (condition.attributeType === null || !condition.key) {
    return new Response([])
  }
  const autocompleter: Autocompleter = {
    fetch_method: 'rest_autocomplete',
    data: {
      ident: VALUE_IDENTS[condition.attributeType],
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

function resolveAttributeType(key: string): AttributeType {
  // A key offered under more than one attribute type is ambiguous: leave it
  // unresolved so the attribute-type dropdown opens for the user to choose.
  const types = keyTypeCache.get(key)
  return types?.size === 1 ? [...types][0]! : null
}

function clearAttributeSelection(): void {
  filterModel.value = []
}

function hasInvalidAttributes(): boolean {
  return (
    resourceAttributes.value.some((attr) => attr.value.trim() === '') ||
    scopeAttributes.value.some((attr) => attr.value.trim() === '') ||
    dataPointAttributes.value.some((attr) => attr.value.trim() === '')
  )
}

function getValidationMessages(): ValidationMessages {
  const messages: ValidationMessages = []
  if (resourceAttributes.value.some((attr) => attr.value.trim() === '')) {
    messages.push({
      message: 'Resource attribute values cannot be empty.',
      location: ['resource_attributes'],
      replacement_value: resourceAttributes.value
    })
  }
  if (scopeAttributes.value.some((attr) => attr.value.trim() === '')) {
    messages.push({
      message: 'Scope attribute values cannot be empty.',
      location: ['scope_attributes'],
      replacement_value: scopeAttributes.value
    })
  }
  if (dataPointAttributes.value.some((attr) => attr.value.trim() === '')) {
    messages.push({
      message: 'Data point attribute values cannot be empty.',
      location: ['data_point_attributes'],
      replacement_value: dataPointAttributes.value
    })
  }
  return messages
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
          :operators="['eq']"
          :query-suggestions="querySuggestions"
          :query-value-suggestions="queryValueSuggestions"
          :resolve-attribute-type="resolveAttributeType"
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
