<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef, MultiSelectPropDef } from '@ucl/_ucl/types/prop-def'

import type { MetricType } from '@/metric-backend/consolidation/types'

import {
  type PresetName,
  type ScopeName,
  presetOptions,
  scopeOptions
} from './consolidationPresets'

const TYPE_OPTIONS: Array<{ title: string; name: MetricType }> = [
  { title: 'Gauge', name: 'gauge' },
  { title: 'Sum', name: 'sum' },
  { title: 'Histogram', name: 'histogram' }
]

export const panelConfig = {
  preset: {
    type: 'list',
    title: 'Preset',
    options: presetOptions,
    help: 'UCL demo only: pick an example consolidation configuration.',
    initialState: 'sumRate'
  },
  availableTypes: {
    type: 'multiselect',
    title: 'Available types',
    options: TYPE_OPTIONS,
    initialState: ['sum'],
    help:
      'UCL demo: the metric types the backend resolved. One shows a plain ' +
      'dropdown, more than one the "Treat as <Type>" grouping. Leave empty for ' +
      'the unknown case: all types are offered.'
  },
  scope: {
    type: 'list',
    title: 'Offered functions',
    options: scopeOptions,
    initialState: 'fullCatalog',
    help:
      'Restricts offered functions per type via the allowedFunctions prop. ' +
      '"Backend-supported" mirrors the custom graph editor: one function per type ' +
      '(gauge last value, sum rate, histogram quantile).'
  }
} satisfies PanelConfigFor<
  typeof FormConsolidation,
  'modelValue' | 'allowedFunctions' | 'label'
> & {
  preset: ListPropDef<PresetName>
  availableTypes: MultiSelectPropDef<MetricType>
  scope: ListPropDef<ScopeName>
}
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { ref, watch } from 'vue'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import {
  DEFAULT_QUANTILE,
  defaultFunction,
  functionSpecsForType
} from '@/metric-backend/consolidation/types'
import type { AllowedFunctions, ConsolidationModel } from '@/metric-backend/consolidation/types'

import { allowedFunctionsScopes, consolidationPresets } from './consolidationPresets'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof FormConsolidation,
  'modelValue' | 'allowedFunctions' | 'label'
>().createRef(panelConfig)

function clonePreset(name: PresetName): ConsolidationModel {
  return structuredClone(consolidationPresets[name])
}

// Keep the selected function within the scope so the demo never shows an option the dropdown omits.
function clampToScope(
  configuration: ConsolidationModel,
  allowed: AllowedFunctions
): ConsolidationModel {
  if (
    functionSpecsForType(configuration.type, allowed).some(
      (spec) => spec.fn === configuration.function
    )
  ) {
    return configuration
  }
  const fn = defaultFunction(configuration.type, allowed)
  return {
    ...fn,
    params: fn.function === 'histogram_quantile' ? { quantile: DEFAULT_QUANTILE } : {},
    lookbackSeconds: configuration.lookbackSeconds
  }
}

const model = ref<ConsolidationModel>(
  clampToScope(clonePreset(propState.value.preset), allowedFunctionsScopes[propState.value.scope])
)

watch(
  () => propState.value.preset,
  (name) => {
    const preset = clampToScope(clonePreset(name), allowedFunctionsScopes[propState.value.scope])
    model.value = preset
    propState.value.availableTypes = [preset.type]
  }
)

watch(
  () => propState.value.scope,
  (name) => {
    model.value = clampToScope(model.value, allowedFunctionsScopes[name])
  }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormConsolidation</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormConsolidation
        v-model="model"
        :available-types="propState.availableTypes"
        :allowed-functions="allowedFunctionsScopes[propState.scope]"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
