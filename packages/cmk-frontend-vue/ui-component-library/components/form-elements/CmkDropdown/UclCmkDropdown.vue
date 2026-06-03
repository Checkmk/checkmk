<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef } from '@ucl/_ucl/types/prop-def'

import { type ButtonVariants } from '@/components/CmkDropdown/CmkDropdownButton.vue'
import { type Suggestions } from '@/components/CmkSuggestions'

import codeExample from './UclCmkDropdownCodeExample.vue?raw'

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

export const panelConfig = {
  optionsType: {
    type: 'list' as const,
    title: 'Options Type',
    options: [
      { title: 'Fixed', name: 'fixed' },
      { title: 'Filtered', name: 'filtered' },
      { title: 'Callback Filtered', name: 'callback' }
    ],
    initialState: 'fixed'
  },
  sectioned: { type: 'boolean' as const, title: 'Sectioned suggestions', initialState: false },
  width: {
    type: 'list' as const,
    title: 'Width',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Wide', name: 'wide' },
      { title: 'Fill', name: 'fill' }
    ] satisfies Options<NonNullable<ButtonVariants['width']>>[],
    initialState: 'default' as const
  },
  disabled: { type: 'boolean' as const, title: 'Disabled', initialState: false },
  required: { type: 'boolean' as const, title: 'Required', initialState: false },
  formValidation: { type: 'boolean' as const, title: 'Form Validation Error', initialState: false },
  inputHint: {
    type: 'string' as const,
    title: 'Input Hint',
    initialState: 'Please select an option...'
  },
  noResultsHint: {
    type: 'string' as const,
    title: 'No Results Hint',
    initialState: 'No matches found'
  },
  modelValue: {
    type: 'list' as const,
    title: 'Selected Option',
    options: [
      { name: '', title: 'None' },
      { name: '1', title: 'Option One' },
      { name: '2', title: 'Option Two' },
      { name: '3', title: 'Option Three' }
    ],
    initialState: ''
  }
} satisfies PanelConfigFor<
  typeof CmkDropdown,
  'label' | 'options' | 'componentId' | 'noElementsText'
> & { optionsType: ListPropDef; sectioned: BoolPropDef }
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
import { computed } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import { Response } from '@/components/CmkSuggestions/suggestions'

import UclCmkDropdownDev from './UclCmkDropdownDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkDropdown,
  'label' | 'options' | 'componentId' | 'noElementsText'
>().createRef(panelConfig)

const selectedOption = computed<string | null>({
  get: () => propState.value.modelValue || null,
  set: (val) => {
    propState.value.modelValue = val ?? ''
  }
})

const dynamicOptions = computed<Suggestions>(() => {
  const baseSuggestions = [
    { name: '1', title: 'Option One' },
    { name: '2', title: 'Option Two' },
    { name: '3', title: 'Option Three' }
  ]

  const sectionedSuggestions = [
    {
      title: 'Primary',
      suggestions: baseSuggestions
    },
    {
      title: 'Secondary',
      suggestions: [
        { name: '4', title: 'Option One Secondary' },
        { name: '5', title: 'Option Two Secondary' }
      ]
    }
  ]

  if (propState.value.optionsType === 'callback') {
    if (propState.value.sectioned) {
      return {
        type: 'callback-filtered',
        querySuggestions: async (query: string) => {
          const lowerCaseQuery = query.toLowerCase()
          return new Response(
            sectionedSuggestions.map((section) => ({
              title: section.title,
              suggestions: section.suggestions.filter((s) =>
                s.title.toLowerCase().includes(lowerCaseQuery)
              )
            }))
          )
        }
      }
    }
    // The two extra rows have a `name` that does not appear in the `title`,
    // so callback queries like `cmk` or `snmp` exercise the name-only-match
    // highlight path — which is only reachable when the backend can match
    // on `name` and return the row even though the title does not contain
    // the query.
    const callbackSuggestions = [
      ...baseSuggestions,
      { name: 'cmk_agent', title: 'Checkmk Agent' },
      { name: 'snmp', title: 'Simple Network Management Protocol' }
    ]
    return {
      type: 'callback-filtered',
      querySuggestions: async (query: string) => {
        const q = query.toLowerCase()
        return new Response(
          callbackSuggestions.filter(
            (s) => s.title.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
          )
        )
      }
    }
  } else if (propState.value.optionsType === 'filtered') {
    return {
      type: 'filtered',
      suggestions: propState.value.sectioned ? sectionedSuggestions : baseSuggestions
    }
  } else {
    return {
      type: 'fixed',
      suggestions: propState.value.sectioned ? sectionedSuggestions : baseSuggestions
    }
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDropdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDropdown
        v-model="selectedOption"
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
