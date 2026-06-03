<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import { type inputSizes } from '@/components/user-input/sizes'

import codeExample from './UclCmkInputCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the input field.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the input field from the next focusable element in reverse order.'
  },
  {
    keys: ['ArrowLeft', 'ArrowRight'],
    description: 'Moves the cursor one character to the left or right within the input content.'
  },
  {
    keys: ['End'],
    description: 'Moves the cursor to the end of the input content.'
  }
]

type InputType = 'text' | 'number' | 'date' | 'time' | 'password'

export const panelConfig = {
  modelValue: {
    type: 'string' as const,
    title: 'Value',
    initialState: 'Checkmk Admin'
  },
  type: {
    type: 'list' as const,
    title: 'Type',
    options: [
      { title: 'Text', name: 'text' },
      { title: 'Number', name: 'number' },
      { title: 'Password', name: 'password' },
      { title: 'Date', name: 'date' },
      { title: 'Time', name: 'time' }
    ] satisfies Options<InputType>[],
    initialState: 'text' as InputType
  },
  fieldSize: {
    type: 'list' as const,
    title: 'Size',
    help: 'This Only affects text inputs and controls the width of the input field.',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'Fill', name: 'fill' }
    ] satisfies Options<keyof typeof inputSizes>[],
    initialState: 'small' as const
  },
  unit: {
    type: 'string' as const,
    title: 'Unit',
    initialState: ''
  },
  inline: {
    type: 'boolean' as const,
    title: 'Inline',
    help: 'When enabled, the input renders inline-block and flows on the same line as surrounding text; when disabled it occupies its own block-level line.',
    initialState: false
  },
  externalErrors: {
    type: 'string' as const,
    title: 'External Error',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkInput>
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

import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkInput>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkInput</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div>
        <CmkInput
          v-model="propState.modelValue"
          :type="propState.type"
          :field-size="propState.fieldSize"
          :unit="propState.unit"
          :inline="propState.inline"
          :external-errors="propState.externalErrors ? [propState.externalErrors] : []"
        />
        <CmkParagraph>Adjacent text to CmkInput </CmkParagraph>
      </div>
      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
