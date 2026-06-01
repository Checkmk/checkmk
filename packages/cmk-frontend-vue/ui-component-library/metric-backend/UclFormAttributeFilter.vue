<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

export const panelConfig = {} satisfies PanelConfigFor<
  typeof FormAttributeFilter,
  'modelValue' | 'querySuggestions' | 'resolveAttributeType' | 'ariaLabel'
>
</script>

<script setup lang="ts">
import {
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import { Response } from '@/components/CmkSuggestions/suggestions'
import type { Section } from '@/components/CmkSuggestions/types'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import type { AttributeFilterModel, AttributeType } from '@/metric-backend/attribute-filter/types'

defineProps<{ screenshotMode: boolean }>()

const filters = ref<AttributeFilterModel>([
  {
    id: crypto.randomUUID(),
    attributeType: 'resource',
    key: 'service.name',
    operator: 'eq',
    value: 'frontend',
    connector: 'AND'
  }
])

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
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormAttributeFilter</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormAttributeFilter
        v-model="filters"
        :query-suggestions="querySuggestions"
        :resolve-attribute-type="resolveAttributeType"
      />
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
