<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type SimpleIcons } from '@/components/CmkIcon'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the button (if not disabled). While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the button and emits the click event.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'

const handleClick = () => {
  console.log('Button clicked!')
}
<${'/'}script>

<template>
  <CmkInlineButton icon="plus" @click="handleClick">
    Add item
  </CmkInlineButton>
</template>`
export const panelConfig = {
  icon: {
    type: 'string',
    title: 'Icon',
    initialState: 'plus',
    help: 'Name of the icon to display. Defaults to "plus" if not set.'
  },
  disabled: {
    type: 'boolean',
    title: 'Disabled',
    initialState: false
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

import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'

import UclCmkInlineButtonDev from './UclCmkInlineButtonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkInlineButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkInlineButton
        :icon="(propState.icon as SimpleIcons) || undefined"
        :disabled="propState.disabled"
      >
        Add item
      </CmkInlineButton>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkInlineButtonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
