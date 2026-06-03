<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkColorPickerCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the color input element. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the color input from the next focusable element in reverse order.'
  },
  {
    keys: ['Space', 'Enter'],
    description: 'Opens the operating system or browser-native color selection dialog.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the color selection dialog if it is open.'
  }
]

export const panelConfig = {
  modelValue: {
    type: 'string' as const,
    title: 'Color',
    initialState: '#ff0000',
    help: 'Controls the selected color value in hexadecimal format.'
  }
} satisfies PanelConfigFor<typeof CmkColorPicker>
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

import CmkColorPicker from '@/components/CmkColorPicker.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkColorPicker>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkColorPicker</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkColorPicker v-model="propState.modelValue" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
