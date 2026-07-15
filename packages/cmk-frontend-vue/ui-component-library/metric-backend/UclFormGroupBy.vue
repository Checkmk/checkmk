<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import { type PresetName, presetOptions } from './groupByPresets'

export const a11yData = [
  {
    keys: ['Enter', 'Space', 'Click'],
    description: 'Opens the group-by clause for editing.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the clause back to its read-only chip and returns focus to it.'
  }
]

export const panelConfig = {
  preset: {
    type: 'list',
    title: 'Preset',
    options: presetOptions,
    help: 'UCL demo only: pick an example group-by configuration.',
    initialState: 'avgByService'
  }
} satisfies PanelConfigFor<typeof FormGroupBy, 'modelValue' | 'ariaLabel'> & {
  preset: ListPropDef<PresetName>
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
import { ref, watch } from 'vue'

import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { GroupByModel } from '@/metric-backend/group-by/types'

import { groupByPresets } from './groupByPresets'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof FormGroupBy, 'modelValue' | 'ariaLabel'>().createRef(
  panelConfig
)

function clonePreset(name: PresetName): GroupByModel {
  return structuredClone(groupByPresets[name])
}

const model = ref<GroupByModel>(clonePreset(propState.value.preset))

watch(
  () => propState.value.preset,
  (name) => {
    model.value = clonePreset(name)
  }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>FormGroupBy</UclDetailPageHeader>

    <UclDetailPageComponent>
      <FormGroupBy v-model="model" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
