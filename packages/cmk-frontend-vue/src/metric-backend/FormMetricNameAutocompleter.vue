<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import {
  ErrorResponse,
  Response,
  type Suggestion,
  WarningResponse,
  flattenSuggestions
} from 'cmk-ui-library/components/CmkSuggestions'
import { fetchRestAPIDeprecated } from 'cmk-ui-library/lib/cmkFetch'
import type { CmkError } from 'cmk-ui-library/lib/error'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import DropdownClearButton from './DropdownClearButton.vue'

const { _t } = usei18n()

const METRIC_NAMES_API = 'api/internal/domain-types/metric_backend/actions/names_with_types/invoke'

interface MetricNameChoice {
  name: string
  types: string[]
}

interface MetricNamesResponse {
  choices: MetricNameChoice[]
  warning?: string | null
}

defineProps<{
  placeholder: TranslatedString
  label?: string
  hasError?: boolean
  disabled?: boolean
}>()

const metricName = defineModel<string | null>('metricName', { default: null })
const metricTypes = defineModel<string[]>('metricTypes', { default: () => [] })

// CmkDropdown surfaces only the selected name, so we remember each fetched metric's
// type(s) here and resolve them by name.
const metricTypesByName = new Map<string, string[]>()

function formatTitle(choice: MetricNameChoice): string {
  return choice.types.length > 0 ? `${choice.name} (${choice.types.join(', ')})` : choice.name
}

function resolveMetricTypes(): void {
  const resolved = metricName.value === null ? [] : (metricTypesByName.get(metricName.value) ?? [])
  // Only write the model when the value actually changed; assigning a fresh array on every
  // query would emit a spurious update:metricTypes on each suggestion fetch.
  if (
    resolved.length !== metricTypes.value.length ||
    resolved.some((type, index) => type !== metricTypes.value[index])
  ) {
    metricTypes.value = resolved
  }
}

const suggestionCache = new Map<string, Response | WarningResponse | ErrorResponse>()
const inflightSuggestions = new Set<string>()
const suggestionRevision = ref(0)

function metricNameEcho(query: string): Suggestion[] {
  if (!query) {
    return []
  }
  const types =
    metricTypesByName.get(query) ?? (query === metricName.value ? metricTypes.value : [])
  return [{ name: query, title: untranslated(formatTitle({ name: query, types })) }]
}

async function fetchMetricNames(
  query: string
): Promise<Response | WarningResponse | ErrorResponse> {
  let result: MetricNamesResponse
  try {
    const response = await fetchRestAPIDeprecated(METRIC_NAMES_API, 'POST', { value: query })
    await response.raiseForStatus()
    result = (await response.json()) as MetricNamesResponse
  } catch (e: unknown) {
    return new ErrorResponse((e as CmkError)?.message || _t('Unknown error'))
  }
  const suggestions: Suggestion[] = []
  for (const choice of result.choices) {
    metricTypesByName.set(choice.name, choice.types)
    suggestions.push({ name: choice.name, title: untranslated(formatTitle(choice)) })
  }
  if (result.warning) {
    return new WarningResponse(result.warning, suggestions)
  }
  return new Response(suggestions)
}

function cachedMetricNames(query: string): Response | WarningResponse | ErrorResponse | undefined {
  const cached = suggestionCache.get(query)
  if (cached) {
    return cached
  }
  if (!inflightSuggestions.has(query)) {
    inflightSuggestions.add(query)
    void fetchMetricNames(query).then((response) => {
      suggestionCache.set(query, response)
      inflightSuggestions.delete(query)
      if (!(response instanceof ErrorResponse)) {
        resolveMetricTypes()
      }
      suggestionRevision.value += 1
    })
  }
  return undefined
}

async function querySuggestions(
  query: string
): Promise<Response | WarningResponse | ErrorResponse> {
  const echo = metricNameEcho(query)
  const cached = cachedMetricNames(query)
  if (!cached) {
    return new Response(echo)
  }
  if (cached instanceof ErrorResponse) {
    // Keep our own echo rather than surfacing the backend error.
    return echo.length > 0 ? new Response(echo) : cached
  }
  const backend = flattenSuggestions(cached.choices)
  const merged = [
    ...echo.filter((entry) => !backend.some((suggestion) => suggestion.name === entry.name)),
    ...backend
  ]
  if (cached instanceof WarningResponse) {
    return new WarningResponse(cached.warning, merged)
  }
  return new Response(merged)
}

watch(metricName, resolveMetricTypes)

// Reading the revision yields a fresh options identity on each settle, so CmkDropdown re-queries.
const dropdownOptions = computed(() => {
  void suggestionRevision.value
  return { type: 'callback-filtered' as const, querySuggestions }
})

const dropdownRef = useTemplateRef<InstanceType<typeof CmkDropdown>>('dropdownRef')

// Clearing unmounts the clear button, so reopen the dropdown: focus returns to the
// input and its suggestions expand so a new metric can be picked right away.
function clearMetricName(): void {
  metricName.value = null
  void nextTick(() => dropdownRef.value?.open())
}
</script>

<template>
  <CmkDropdown
    ref="dropdownRef"
    v-model="metricName"
    floating
    :options="dropdownOptions"
    :input-hint="placeholder"
    :label="untranslated(label || '')"
    :width="'wide'"
    :no-results-hint="_t('No results found')"
    :form-validation="hasError || false"
    :disabled="disabled || false"
  >
    <template v-if="metricName !== null && !disabled" #buttons-end>
      <DropdownClearButton @clear="clearMetricName" />
    </template>
  </CmkDropdown>
</template>
