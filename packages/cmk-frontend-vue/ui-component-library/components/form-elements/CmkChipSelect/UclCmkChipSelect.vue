<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkChipSelectCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Enter', 'Space'],
    description: 'Opens the chip and, when open, selects the highlighted option.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the option list without making a selection and restores focus to the chip.'
  },
  {
    keys: ['ArrowDown', 'ArrowUp'],
    description: 'Moves the active highlight to the next/previous selectable option.'
  }
]

export const panelConfig = {
  optionsType: {
    type: 'list' as const,
    title: 'Options Type',
    options: [
      { title: 'Fixed', name: 'fixed' },
      { title: 'Filtered', name: 'filtered' }
    ],
    initialState: 'fixed'
  },
  disabled: { type: 'boolean' as const, title: 'Disabled', initialState: false },
  inputHint: {
    type: 'string' as const,
    title: 'Input Hint',
    initialState: 'More ranges'
  },
  noResultsHint: {
    type: 'string' as const,
    title: 'No Results Hint',
    initialState: 'No matching ranges'
  }
} satisfies PanelConfigFor<typeof CmkChipSelect, 'label' | 'options' | 'modelValue'> & {
  optionsType: ListPropDef
}
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { computed, ref } from 'vue'

import CmkChipSelect from '@/components/CmkChipSelect.vue'
import { type Suggestions } from '@/components/CmkSuggestions'

import UclCmkChipSelectDev from './UclCmkChipSelectDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkChipSelect,
  'label' | 'options' | 'modelValue'
>().createRef(panelConfig)

const selected = ref<string | null>(null)

const demoSuggestions = [
  { name: '1h', title: 'Last hour' },
  { name: '3h', title: 'Last 3 hours' },
  { name: '1d', title: 'Last day' },
  { name: '1w', title: 'Last week' }
]

const options = computed<Suggestions>(() => ({
  type: propState.value.optionsType as 'fixed' | 'filtered',
  suggestions: demoSuggestions
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkChipSelect</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkChipSelect
        v-model="selected"
        :options="options"
        :input-hint="propState.inputHint"
        :no-results-hint="propState.noResultsHint"
        :disabled="propState.disabled"
        label="demo chip select"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkChipSelectDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
