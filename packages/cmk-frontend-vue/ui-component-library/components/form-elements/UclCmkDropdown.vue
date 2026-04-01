<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type ButtonVariants } from '@/components/CmkDropdown/CmkDropdownButton.vue'
import { type Suggestions } from '@/components/CmkSuggestions'

export const a11yData = [
  {
    keys: ['Enter', 'Space'],
    description: 'Selects the currently highlighted suggestion and triggers the update.'
  },
  {
    keys: ['Tab'],
    description:
      'Moves focus to the dropdown from the previous focusable element, or selects the currently highlighted suggestion when the dropdown is open.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the dropdown from the next focusable element in reverse order.'
  },
  {
    keys: ['Escape'],
    description:
      'Closes the suggestions dropdown or removes focus from the filter input without making a selection.'
  },
  {
    keys: ['ArrowDown', 'ArrowUp'],
    description:
      'Moves the active highlight to the next selectable suggestion in the list, scrolling it into view if necessary.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import type { Suggestions } from '@/components/CmkSuggestions'

const selected = ref<string | null>(null)
const options: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: '1', title: 'one' },
    { name: '2', title: 'two' }
  ]
}
<${'/'}script>

<template>
  <CmkDropdown
    v-model:selected-option="selected"
    :options="options"
    input-hint="Input Hint"
    no-results-hint="No Results Hint"
    label="demo dropdown"
    required
  />
</template>`
export const panelConfig = {
  optionsType: {
    type: 'list',
    title: 'Options Type',
    options: [
      { title: 'Fixed', name: 'fixed' },
      { title: 'Filtered', name: 'filtered' },
      { title: 'Callback Filtered', name: 'callback' }
    ],
    initialState: 'fixed'
  },
  width: {
    type: 'list',
    title: 'Width',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Wide', name: 'wide' },
      { title: 'Fill', name: 'fill' }
    ] satisfies Options<NonNullable<ButtonVariants['width']>>[],
    initialState: 'default' as const
  },
  disabled: { type: 'boolean', title: 'Disabled', initialState: false },
  required: { type: 'boolean', title: 'Required', initialState: false },
  formValidation: { type: 'boolean', title: 'Form Validation Error', initialState: false },
  inputHint: { type: 'string', title: 'Input Hint', initialState: 'Please select an option...' },
  noResultsHint: { type: 'string', title: 'No Results Hint', initialState: 'No matches found' },
  selectedOption: {
    type: 'list',
    title: 'Selected Option',
    options: [
      { name: '', title: 'None' },
      { name: '1', title: 'Option One' },
      { name: '2', title: 'Option Two' },
      { name: '3', title: 'Option Three' }
    ],
    initialState: ''
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { computed, ref } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import { Response } from '@/components/CmkSuggestions/suggestions'

import UclCmkDropdownDev from './UclCmkDropdownDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

const selectedOption = computed<string | null>({
  get: () => propState.value.selectedOption || null,
  set: (val) => {
    propState.value.selectedOption = val ?? ''
  }
})

const dynamicOptions = computed<Suggestions>(() => {
  const baseSuggestions = [
    { name: '1', title: 'Option One' },
    { name: '2', title: 'Option Two' },
    { name: '3', title: 'Option Three' }
  ]

  if (propState.value.optionsType === 'callback') {
    return {
      type: 'callback-filtered',
      querySuggestions: async (query: string) =>
        new Response(
          baseSuggestions.filter(
            (s) => s.title.toLowerCase().includes(query.toLowerCase()) || s.name === query
          )
        )
    }
  } else if (propState.value.optionsType === 'filtered') {
    return { type: 'filtered', suggestions: baseSuggestions }
  } else {
    return { type: 'fixed', suggestions: baseSuggestions }
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDropdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDropdown
        v-model:selected-option="selectedOption"
        :options="dynamicOptions"
        :input-hint="propState.inputHint"
        :no-results-hint="propState.noResultsHint"
        :width="propState.width"
        :disabled="propState.disabled"
        :required="propState.required"
        label="demo dropdown"
        :form-validation="propState.formValidation"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkDropdownDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
