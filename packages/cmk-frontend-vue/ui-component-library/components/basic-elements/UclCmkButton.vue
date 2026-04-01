<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type ButtonVariants } from '@/components/CmkButton.vue'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the button or link element (if not disabled). While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Activates the button. If rendered as a link (via the href prop), Enter follows the link.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} CmkButton from '@/components/CmkButton.vue'

const handleClick = () => {
  console.log('Button clicked!')
}
<${'/'}script>

<template>
  <CmkButton variant="primary" @click="handleClick">
    Click Me
  </CmkButton>
</template>`
export const panelConfig = {
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Optional', name: 'optional' },
      { title: 'Primary', name: 'primary' },
      { title: 'Secondary', name: 'secondary' },
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' },
      { title: 'Info', name: 'info' }
    ] satisfies Options<ButtonVariants['variant']>[],
    initialState: 'optional' as const
  },
  disabled: {
    type: 'boolean',
    title: 'Disabled',
    initialState: false
  },
  href: {
    type: 'string',
    title: 'Href',
    initialState: '',
    help: 'Href attribute renders as a link.'
  },
  target: {
    type: 'list',
    title: 'Target',
    options: [
      { title: 'None', name: '' },
      { title: '_blank', name: '_blank' },
      { title: '_self', name: '_self' }
    ],
    initialState: '',
    help: 'Only applicable if href is set. Specifies where to open the linked document.'
  },
  title: {
    type: 'string',
    title: 'Title Attribute',
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

import CmkButton from '@/components/CmkButton.vue'

import UclCmkButtonDev from './UclCmkButtonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton
        :variant="propState.variant"
        :disabled="propState.disabled"
        :href="propState.href || undefined"
        :target="propState.target || undefined"
        :title="propState.title"
      >
        Click Me
      </CmkButton>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkButtonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
