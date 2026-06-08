<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkRadioButtonCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus into the radio group, landing on the selected radio button (or the first one if none is selected).'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus out of the radio group to the previous focusable element.'
  },
  {
    keys: ['↑', '↓', '←', '→'],
    description:
      'Moves focus to the previous/next radio button within the group and selects it, enforcing mutual exclusion.'
  },
  {
    keys: ['Space'],
    description: 'Selects the focused radio button.'
  }
]

export const rangeOptions: Options<string>[] = [
  { title: 'Today', name: 'today' },
  { title: 'Yesterday', name: 'yesterday' },
  { title: 'This week', name: 'week' },
  { title: 'This month', name: 'month' },
  { title: 'This year', name: 'year' },
  { title: 'Custom', name: 'custom' }
]

export const panelConfig = {
  modelValue: {
    type: 'list' as const,
    title: 'Selected',
    options: rangeOptions,
    initialState: 'custom'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'Disabled',
    initialState: false
  },
  externalErrors: {
    type: 'string' as const,
    title: 'External Error Message',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkRadioGroup, 'label'>
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

import { CmkRadioButton, CmkRadioGroup } from '@/components/user-input/CmkRadioButton'

import UclCmkRadioButtonDev from './UclCmkRadioButtonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkRadioGroup, 'label'>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkRadioButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkRadioGroup
        v-model="propState.modelValue"
        label="Time range"
        :disabled="propState.disabled"
        :external-errors="propState.externalErrors ? [propState.externalErrors] : []"
      >
        <CmkRadioButton
          v-for="option in rangeOptions"
          :key="option.name"
          :value="option.name"
          :label="option.title"
          :disabled="option.name === 'year'"
          v-bind="option.name === 'week' ? { help: 'The current calendar week.' } : {}"
        />
      </CmkRadioGroup>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkRadioButtonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
