<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the checkbox. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the checkbox from the next focusable element in reverse order.'
  },
  {
    keys: ['Space'],
    description: 'Toggles the checkbox state between checked and unchecked.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

const isChecked = ref(false)
<${'/'}script>

<template>
  <CmkCheckbox
    v-model="isChecked"
    label="Enable notifications"
    help="You will receive alerts via email."
  />
</template>`

type CheckboxPadding = 'both' | 'top' | 'bottom'

export const panelConfig = {
  modelValue: {
    type: 'boolean',
    title: 'Checked',
    initialState: false
  },
  label: {
    type: 'string',
    title: 'Label',
    initialState: 'Enable notifications'
  },
  help: {
    type: 'string',
    title: 'Help Text',
    initialState: 'You will receive alerts via email.'
  },
  disabled: {
    type: 'boolean',
    title: 'Disabled',
    initialState: false
  },
  padding: {
    type: 'list',
    title: 'Padding',
    options: [
      { title: 'Both', name: 'both' },
      { title: 'Top', name: 'top' },
      { title: 'Bottom', name: 'bottom' }
    ] satisfies Options<CheckboxPadding>[],

    initialState: 'both' as const
  },
  dots: {
    type: 'boolean',
    title: 'Show Dots',
    initialState: false
  },
  externalErrors: {
    type: 'string',
    title: 'External Error Message',
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
import { ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import UclCmkCheckboxDev from './UclCmkCheckboxDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCheckbox</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCheckbox
        v-model="propState.modelValue"
        :label="propState.label"
        :help="propState.help"
        :disabled="propState.disabled"
        :padding="propState.padding"
        :dots="propState.dots"
        :external-errors="propState.externalErrors ? [propState.externalErrors] : []"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCheckboxDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
