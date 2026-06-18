<!--
Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { watch } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch'
import type { CmkError } from '@/lib/error'
import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkDropdown from '@/components/CmkDropdown'
import {
  ErrorResponse,
  Response,
  type Suggestion,
  WarningResponse
} from '@/components/CmkSuggestions'

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

async function querySuggestions(
  query: string
): Promise<ErrorResponse | WarningResponse | Response> {
  let result: MetricNamesResponse
  try {
    const response = await fetchRestAPI(METRIC_NAMES_API, 'POST', { value: query })
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

  // CmkDropdown re-queries for the current selection on mount and on change, so this
  // resolves the type of a preset (e.g. saved) metric name once it becomes known.
  resolveMetricTypes()

  if (result.warning) {
    return new WarningResponse(result.warning, suggestions)
  }
  return new Response(suggestions)
}

watch(metricName, resolveMetricTypes)

// Keep a stable reference: an inline object literal would change identity on every render
// and retrigger CmkDropdown's/CmkSuggestions' suggestion watchers.
const dropdownOptions = { type: 'callback-filtered' as const, querySuggestions }
</script>

<template>
  <CmkDropdown
    v-model="metricName"
    :options="dropdownOptions"
    :input-hint="placeholder"
    :label="untranslated(label || '')"
    :width="'wide'"
    :no-results-hint="_t('No results found')"
    :form-validation="hasError || false"
    :disabled="disabled || false"
  />
</template>
