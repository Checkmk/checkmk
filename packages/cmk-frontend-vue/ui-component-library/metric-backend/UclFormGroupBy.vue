<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import type { GroupByInputType } from '@/metric-backend/group-by/types'

import { type PresetName, presetOptions } from './groupByPresets'

export const a11yData = [
  {
    keys: ['Enter', 'Space', 'Click'],
    description:
      'Opens the group-by clause for editing, or — once open — activates the focused control: ' +
      'opens a key pill or triggers a button. Only one key pill is editable at a time; activating ' +
      'another control commits the open pill if its key is set, otherwise the pill stays open and ' +
      'reveals its validation error.'
  },
  {
    keys: ['Tab'],
    description:
      'Moves focus forward through the grouping function, its parameters and the key pills ' +
      '(including the inputs of the currently open pill).'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus backward through the same elements.'
  },
  {
    keys: ['Escape'],
    description:
      'Closes the open key pill (or the whole clause) back to its read-only chip and returns focus ' +
      'to it. A pill with an empty key stays open and reveals its validation error. If a dropdown ' +
      'is open, only the dropdown closes.'
  }
]

const INPUT_TYPE_OPTIONS: Array<{ title: string; name: GroupByInputType }> = [
  { title: 'Float consolidation', name: 'float' },
  { title: 'Histogram passthrough', name: 'histogram' }
]

export const panelConfig = {
  preset: {
    type: 'list',
    title: 'Preset',
    options: presetOptions,
    help: 'UCL demo only: pick an example group-by configuration.',
    initialState: 'avgByService'
  },
  inputType: {
    type: 'list',
    title: 'Consolidation output',
    options: INPUT_TYPE_OPTIONS,
    initialState: 'float',
    help: 'The consolidation output type on the same graph line; selects the offered functions.'
  }
} satisfies PanelConfigFor<
  typeof FormGroupBy,
  'modelValue' | 'querySuggestions' | 'resolveLevel' | 'ariaLabel'
> & {
  preset: ListPropDef<PresetName>
  inputType: ListPropDef<GroupByInputType>
}
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
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import type { Section } from 'cmk-ui-library/components/CmkSuggestions/types'
import { ref, watch } from 'vue'

import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { GroupByModel, GroupLevel } from '@/metric-backend/group-by/types'

import { groupByPresets, presetInputType } from './groupByPresets'

defineProps<{ screenshotMode: boolean }>()

interface TypedSection extends Section {
  level: GroupLevel
}

const dummyKeySections: TypedSection[] = [
  {
    level: 'resource',
    title: 'Resource',
    suggestions: [
      { name: 'service.name', title: 'service.name' },
      { name: 'host.name', title: 'host.name' },
      { name: 'deployment.environment', title: 'deployment.environment' },
      { name: 'k8s.namespace.name', title: 'k8s.namespace.name' }
    ]
  },
  {
    level: 'scope',
    title: 'Scope',
    suggestions: [
      { name: 'otel.library.name', title: 'otel.library.name' },
      { name: 'otel.library.version', title: 'otel.library.version' }
    ]
  },
  {
    level: 'data_point',
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
      suggestions: section.suggestions.filter((s) => s.title.toLowerCase().includes(needle))
    }))
    .filter((section) => section.suggestions.length > 0)
  // Mirror the backend: prepend the typed query so a custom key stays selectable.
  const trimmed = query.trim()
  const trimmedLower = trimmed.toLowerCase()
  if (
    trimmed === '' ||
    filtered.some((s) => s.suggestions.some((i) => i.title.toLowerCase() === trimmedLower))
  ) {
    return new Response(filtered)
  }
  return new Response([
    { title: 'Custom', suggestions: [{ name: trimmed, title: trimmed }] },
    ...filtered
  ])
}

function resolveLevel(key: string): GroupLevel | null {
  const section = dummyKeySections.find((s) => s.suggestions.some((sug) => sug.name === key))
  return section?.level ?? null
}

const propState = new PanelStateCreator<
  typeof FormGroupBy,
  'modelValue' | 'querySuggestions' | 'resolveLevel' | 'ariaLabel'
>().createRef(panelConfig)

function clonePreset(name: PresetName): GroupByModel {
  return structuredClone(groupByPresets[name])
}

const model = ref<GroupByModel>(clonePreset(propState.value.preset))

watch(
  () => propState.value.preset,
  (name) => {
    model.value = clonePreset(name)
    propState.value.inputType = presetInputType[name]
  }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormGroupBy</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormGroupBy
        v-model="model"
        :input-type="propState.inputType"
        :query-suggestions="querySuggestions"
        :resolve-level="resolveLevel"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
