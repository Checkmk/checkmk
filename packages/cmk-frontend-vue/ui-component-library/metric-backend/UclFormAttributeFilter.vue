<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef, MultiSelectPropDef } from '@ucl/_ucl/types/prop-def'

import { EXISTENCE_OPERATORS, STRING_OPERATORS } from '@/metric-backend/attribute-filter/types'
import type { Operator } from '@/metric-backend/attribute-filter/types'

import { type PresetName, presetOptions } from './attributeFilterPresets'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves focus forward through the filter chips and through the inputs of the currently open pill.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus backward through the same elements.'
  },
  {
    keys: ['Enter', 'Space', 'Click'],
    description:
      'Activates the focused element — opens a pill for editing or triggers a button. Only one pill is editable at a time; activating another control commits the open pill if valid, otherwise the pill stays open and its validation errors are revealed.'
  },
  {
    keys: ['Escape'],
    description:
      'Closes the open pill back to its read-only chip and returns focus to it. A pill with any required field empty stays open and reveals validation errors. If a dropdown inside the pill is open, only the dropdown closes.'
  }
]

const ALL_OPERATORS: Operator[] = [...STRING_OPERATORS, ...EXISTENCE_OPERATORS]

// Plain-string mirror of operatorPhrases() in pill-label.ts: panelConfig labels
// cannot use the i18n helper because it runs at module load, before i18n is set up.
const OPERATOR_LABELS: Record<Operator, string> = {
  eq: 'is',
  neq: 'is not',
  contains: 'contains',
  not_contains: 'does not contain',
  starts_with: 'starts with',
  not_starts_with: 'does not start with',
  ends_with: 'ends with',
  not_ends_with: 'does not end with',
  regex: 'matches regex',
  not_regex: 'does not match regex',
  exists: 'exists',
  not_exists: 'does not exist'
}

const operatorOptions = ALL_OPERATORS.map((name) => ({ name, title: OPERATOR_LABELS[name] }))

export const panelConfig = {
  preset: {
    type: 'list',
    title: 'Preset',
    options: presetOptions,
    initialState: 'empty'
  },
  operators: {
    type: 'multiselect',
    title: 'Operators',
    options: operatorOptions,
    initialState: [...ALL_OPERATORS],
    help: 'Changing the available operators after conditions already exist is a dev-tooling artifact, not a component scenario: a caller fixes the operator set up front. Narrowing to a single existence operator clears each value; widening back to a comparison operator leaves those values empty and the conditions model-invalid, but existing closed pills are not re-opened so the invalid state is not shown. In real usage the operator set does not change at runtime.'
  }
} satisfies PanelConfigFor<
  typeof FormAttributeFilter,
  'modelValue' | 'querySuggestions' | 'queryValueSuggestions' | 'resolveAttributeType' | 'ariaLabel'
> & { preset: ListPropDef<PresetName>; operators: MultiSelectPropDef<Operator> }
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { computed, ref, watch } from 'vue'

import { Response } from '@/components/CmkSuggestions/suggestions'
import type { Section } from '@/components/CmkSuggestions/types'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import type {
  AttributeCondition,
  AttributeFilterModel,
  AttributeType
} from '@/metric-backend/attribute-filter/types'

import { filterPresets } from './attributeFilterPresets'

defineProps<{ screenshotMode: boolean }>()

interface TypedSection extends Section {
  attributeType: Exclude<AttributeType, null>
}

const dummyKeySections: TypedSection[] = [
  {
    attributeType: 'resource',
    title: 'Resource',
    suggestions: [
      { name: 'service.name', title: 'service.name' },
      { name: 'host.name', title: 'host.name' },
      { name: 'deployment.environment', title: 'deployment.environment' },
      { name: 'k8s.namespace.name', title: 'k8s.namespace.name' }
    ]
  },
  {
    attributeType: 'scope',
    title: 'Scope',
    suggestions: [
      { name: 'otel.library.name', title: 'otel.library.name' },
      { name: 'otel.library.version', title: 'otel.library.version' }
    ]
  },
  {
    attributeType: 'datapoint',
    title: 'Data point',
    suggestions: [
      { name: 'http.method', title: 'http.method' },
      { name: 'http.route', title: 'http.route' },
      { name: 'http.status_code', title: 'http.status_code' }
    ]
  }
]

async function querySuggestions(query: string): Promise<Response> {
  const needle = query.toLowerCase()
  const filtered = dummyKeySections
    .map((section) => ({
      title: section.title,
      suggestions: section.suggestions.filter(
        (s) =>
          (s.name ?? '').toLowerCase().includes(needle) || s.title.toLowerCase().includes(needle)
      )
    }))
    .filter((section) => section.suggestions.length > 0)
  // Mirror the backend `_autocomplete_options` contract: prepend the typed
  // query as a selectable option so the user can confirm a custom key.
  const trimmed = query.trim()
  const trimmedLower = trimmed.toLowerCase()
  if (
    trimmed === '' ||
    filtered.some((s) => s.suggestions.some((i) => (i.name ?? '').toLowerCase() === trimmedLower))
  ) {
    return new Response(filtered)
  }
  return new Response([
    { title: 'Custom', suggestions: [{ name: trimmed, title: trimmed }] },
    ...filtered
  ])
}

function resolveAttributeType(key: string): AttributeType {
  const section = dummyKeySections.find((s) => s.suggestions.some((sug) => sug.name === key))
  return section?.attributeType ?? null
}

const dummyValuePresets: Record<string, string[]> = {
  'service.name': ['frontend', 'checkout', 'payments'],
  'http.method': ['GET', 'POST', 'PUT', 'DELETE'],
  'http.status_code': ['200', '404', '500']
}

async function queryValueSuggestions(
  condition: AttributeCondition,
  query: string
): Promise<Response> {
  const needle = query.toLowerCase()
  const presets = condition.key !== null ? (dummyValuePresets[condition.key] ?? []) : []
  const matches = presets
    .filter((v: string) => v.toLowerCase().includes(needle))
    .map((v: string) => ({ name: v, title: v }))
  // Echo the typed query so free-text entry is selectable (mirrors the real backend).
  if (query !== '' && !matches.some((m: { name: string }) => m.name === query)) {
    matches.push({ name: query, title: query })
  }
  return new Response(matches)
}

const propState = new PanelStateCreator<
  typeof FormAttributeFilter,
  'modelValue' | 'querySuggestions' | 'queryValueSuggestions' | 'resolveAttributeType' | 'ariaLabel'
>().createRef(panelConfig)

function clonePreset(name: PresetName): AttributeFilterModel {
  return structuredClone(filterPresets[name])
}

const filters = ref<AttributeFilterModel>(clonePreset(propState.value.preset))

watch(
  () => propState.value.preset,
  (name) => {
    filters.value = clonePreset(name)
  }
)

const selectedOperators = computed(() => propState.value.operators)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormAttributeFilter</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormAttributeFilter
        v-model="filters"
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        :resolve-attribute-type="resolveAttributeType"
        :operators="selectedOperators"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
