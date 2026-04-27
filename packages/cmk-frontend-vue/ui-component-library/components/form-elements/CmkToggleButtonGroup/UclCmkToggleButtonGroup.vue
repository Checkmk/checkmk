<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type ToggleButtonOption } from '@/components/CmkToggleButtonGroup.vue'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus through the individual toggle buttons. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the individual toggle buttons.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Selects the currently focused toggle option.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

const currentView = ref('list')

const viewOptions = [
  { label: 'List View', value: 'list' },
  { label: 'Grid View', value: 'grid' }

]
<${'/'}script>

<template>
  <CmkToggleButtonGroup
    v-model="currentView"
    :options="viewOptions"
  />
</template>`
export const panelConfig = {
  modelValue: {
    type: 'list',
    title: 'Selected Value',
    options: [
      { title: 'list', name: 'list' },
      { title: 'grid', name: 'grid' },
      { title: 'map', name: 'map' }
    ] satisfies Options<string>[],
    initialState: 'list' as const
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

defineProps<{ screenshotMode: boolean }>()

const demoOptions: ToggleButtonOption[] = [
  { label: 'List View', value: 'list', tooltip: 'Display items in a vertical list' },
  { label: 'Grid View', value: 'grid', tooltip: 'Display items in a grid layout' },
  {
    label: 'Map View',
    value: 'map',
    disabled: true,
    disabledTooltip: 'Requires Checkmk Pro edition'
  }
]

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkToggleButtonGroup</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkToggleButtonGroup v-model="propState.modelValue" :options="demoOptions" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
