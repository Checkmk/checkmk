<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import CmkPaste from '@/components/CmkPaste.vue'

import codeExample from './UclCmkPasteCodeExample.vue?raw'

export const a11yDataCmkPaste = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus through the Paste button and the input field.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the Paste button and the input field.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Triggers the paste action and opens the confirmation tooltip, assuming an interactive element (like a button) is provided in the trigger slot.'
  },
  {
    keys: ['Escape'],
    description: 'Dismisses the active tooltip if it is currently visible.'
  }
]

export const panelConfig = {
  inputFirst: { type: 'boolean' as const, title: 'Input first', initialState: false }
} satisfies PanelConfigFor<typeof CmkPaste>
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
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'

import UclCmkPasteDev from './UclCmkPasteDev.vue'

defineProps<{ screenshotMode: boolean }>()

const inputValue = ref('')

const propState = new PanelStateCreator<typeof CmkPaste>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPaste</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkPaste :input-first="propState.inputFirst">
        <template #trigger>
          <CmkButton variant="secondary">Paste</CmkButton>
        </template>
        <template #input>
          <input v-model="inputValue" style="padding: var(--dimension-3)" />
        </template>
      </CmkPaste>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yDataCmkPaste" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkPasteDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
