<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type Colors, type Sizes, type Variants } from '@/components/CmkChip.vue'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves focus to the chip if it is rendered as a button and is not disabled.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the chip from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Triggers the click event if the chip is rendered as an interactive button.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} CmkChip from '@/components/CmkChip.vue'
<${'/'}script>

<template>
  <CmkChip
    size="medium"
    color="success"
    variant="fill"
  >
    Demo Chip
  </CmkChip>
</template>`
export const panelConfig = {
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<Sizes>[],
    initialState: 'medium' as const
  },
  color: {
    type: 'list',
    title: 'Color',
    options: [
      { title: 'Success(Green)', name: 'success' },
      { title: 'Hosts (Blue)', name: 'hosts' },
      { title: 'Info (Blue)', name: 'info' },
      { title: 'Warning (Yellow)', name: 'warning' },
      { title: 'Services (Yellow)', name: 'services' },
      { title: 'Danger (Red)', name: 'danger' },
      { title: 'Customization (Pink)', name: 'customization' },
      { title: 'Others (Grey)', name: 'others' },
      { title: 'Users (Purple)', name: 'users' },
      { title: 'Special Agents (Cyan)', name: 'specialAgents' }
    ] satisfies Options<Colors>[],
    initialState: 'success' as const
  },
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Fill', name: 'fill' },
      { title: 'Outline', name: 'outline' }
    ] satisfies Options<Variants>[],
    initialState: 'fill' as const
  },
  asDiv: { type: 'boolean', title: 'Render as Div', initialState: false },
  disabled: { type: 'boolean', title: 'Disabled', initialState: false }
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

import CmkChip from '@/components/CmkChip.vue'

import UclCmkChipDev from './UclCmkChipDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkChip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkChip
        :size="propState.size"
        :color="propState.color"
        :variant="propState.variant"
        :as-div="propState.asDiv"
        :disabled="propState.disabled"
      >
        Demo Chip
      </CmkChip>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkChipDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
