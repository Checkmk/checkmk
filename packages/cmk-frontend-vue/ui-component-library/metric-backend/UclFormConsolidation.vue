<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import { type PresetName, presetOptions } from './consolidationPresets'

export const panelConfig = {
  preset: {
    type: 'list',
    title: 'Preset',
    options: presetOptions,
    help: 'UCL demo only: pick an example consolidation configuration.',
    initialState: 'sumRate'
  }
} satisfies PanelConfigFor<typeof FormConsolidation, 'modelValue'> & {
  preset: ListPropDef<PresetName>
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
      <FormConsolidation v-model="model" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>
  </UclDetailPageLayout>
</template>
