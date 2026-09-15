<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type Colors, type Sizes, type Variants } from 'cmk-ui-library/components/CmkChip.vue'

import codeExample from './UclCmkChipCodeExample.vue?raw'

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

export const panelConfig = {
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<Sizes>({
      small: 'Small',
      medium: 'Medium',
      large: 'Large'
    }),
    initialState: 'medium' as const
  },
  color: {
    type: 'list' as const,
    title: 'Color',
    options: listOptions<Colors>({
      success: 'Success(Green)',
      hosts: 'Hosts (Blue)',
      info: 'Info (Blue)',
      warning: 'Warning (Yellow)',
      services: 'Services (Yellow)',
      danger: 'Danger (Red)',
      customization: 'Customization (Pink)',
      others: 'Others (Grey)',
      users: 'Users (Purple)',
      specialAgents: 'Special Agents (Cyan)'
    }),
    initialState: 'success' as const
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<Variants>({
      fill: 'Fill',
      outline: 'Outline'
    }),
    initialState: 'fill' as const
  },
  asDiv: {
    type: 'boolean' as const,
    title: 'Non-interactive (as div)',
    initialState: false,
    help: 'Renders the chip as a div instead of a button. Use for non-interactive display purposes.'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'Disabled',
    initialState: false,
    help: 'No Effect when rendered as a div. A div is non-interactive by nature, therefore cannot be set to disabled.'
  }
} satisfies PanelConfigFor<typeof CmkChip>
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
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'

import UclCmkChipDev from './UclCmkChipDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkChip>().createRef(panelConfig)
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
