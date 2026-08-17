<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ButtonVariants } from 'cmk-ui-library/components/CmkDropdown/CmkDropdownButton.vue'

import codeExample from './UclCmkAddDropdownCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Enter', 'Space'],
    description: 'Selects the currently highlighted suggestion and triggers the add.'
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
    description: 'Closes the suggestions dropdown without adding anything.'
  },
  {
    keys: ['ArrowDown', 'ArrowUp'],
    description:
      'Moves the active highlight to the next selectable suggestion in the list, scrolling it into view if necessary.'
  }
]

export const panelConfig = {
  label: {
    type: 'string' as const,
    title: 'Label',
    initialState: 'Add metric'
  },
  width: {
    type: 'list' as const,
    title: 'Width',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Wide', name: 'wide' },
      { title: 'Fill', name: 'fill' }
    ] satisfies Options<ButtonVariants['width']>[],
    initialState: 'default' as const
  },
  floating: {
    type: 'boolean' as const,
    title: 'Floating',
    initialState: false
  }
} satisfies PanelConfigFor<typeof CmkAddDropdown, 'options' | 'componentId'>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import CmkAddDropdown from 'cmk-ui-library/components/CmkDropdown/CmkAddDropdown.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkAddDropdown,
  'options' | 'componentId'
>().createRef(panelConfig)

const options: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'cpu', title: 'CPU utilization' },
    { name: 'memory', title: 'Memory usage' },
    { name: 'disk_io', title: 'Disk IO' }
  ]
}

const added = ref<string[]>([])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAddDropdown</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAddDropdown
        :options="options"
        :label="propState.label"
        :width="propState.width"
        :floating="propState.floating"
        @select="(value) => added.push(value)"
      />
      <p v-if="added.length > 0">Added: {{ added.join(', ') }}</p>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
