<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef, MultiSelectPropDef } from '@ucl/_ucl/types/prop-def'

import type { MetricType } from '@/metric-backend/consolidation/types'

import { type PresetName, presetOptions } from './consolidationPresets'

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
  }
} satisfies PanelConfigFor<typeof FormConsolidation, 'modelValue'> & {
  preset: ListPropDef<PresetName>
  availableTypes: MultiSelectPropDef<MetricType>
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
import type { ConsolidationModel } from '@/metric-backend/consolidation/types'

import { consolidationPresets } from './consolidationPresets'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof FormConsolidation, 'modelValue'>().createRef(
  panelConfig
)

function clonePreset(name: PresetName): ConsolidationModel {
  return structuredClone(consolidationPresets[name])
}

const model = ref<ConsolidationModel>(clonePreset(propState.value.preset))

watch(
  () => propState.value.preset,
  (name) => {
    model.value = clonePreset(name)
  }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormConsolidation</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormConsolidation v-model="model" :available-types="propState.availableTypes" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
