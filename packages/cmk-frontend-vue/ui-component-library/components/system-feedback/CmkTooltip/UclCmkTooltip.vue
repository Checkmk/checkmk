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
      'Moves keyboard focus to the button or link element (if not disabled). While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Opens the help text.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the tooltip if it is currently open.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'

${'import'} CmkButton from '@/components/CmkButton.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

const isTooltipOpen = ref(false)
<${'/'}script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip v-model:open="isTooltipOpen">

      <CmkTooltipTrigger as-child>
        <CmkButton variant="secondary">Interact with me</CmkButton>
      </CmkTooltipTrigger>

      <CmkTooltipContent side="top" align="center">
        <div class="tooltip-content">
          This is a tooltip on the top!
        </div>
      </CmkTooltipContent>

    </CmkTooltip>
  </CmkTooltipProvider>
</template>`

type SideOptions = 'top' | 'right' | 'bottom' | 'left'
type AlignOptions = 'start' | 'center' | 'end'

export const panelConfig = {
  open: { type: 'boolean', title: 'Open', initialState: false },
  disableClosingTrigger: { type: 'boolean', title: 'Disable Closing Trigger', initialState: false },
  side: {
    type: 'list',
    title: 'Side',
    options: [
      { title: 'Top', name: 'top' },
      { title: 'Right', name: 'right' },
      { title: 'Bottom', name: 'bottom' },
      { title: 'Left', name: 'left' }
    ] satisfies Options<SideOptions>[],
    initialState: 'top' as SideOptions
  },
  align: {
    type: 'list',
    title: 'Align',
    options: [
      { title: 'Start', name: 'start' },
      { title: 'Center', name: 'center' },
      { title: 'End', name: 'end' }
    ] satisfies Options<AlignOptions>[],
    initialState: 'center' as AlignOptions
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTooltip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTooltipProvider>
        <CmkTooltip
          v-model:open="propState.open"
          :disable-closing-trigger="propState.disableClosingTrigger"
        >
          <CmkTooltipTrigger as-child>
            <CmkButton variant="secondary" @click="propState.open = !propState.open">
              <CmkIcon name="checkmark" variant="inline" size="small" />
              <span>Interact with me</span>
            </CmkButton>
          </CmkTooltipTrigger>

          <CmkTooltipContent
            :side="propState.side"
            :align="propState.align"
            @pointer-down-outside="propState.open = false"
          >
            <CmkIcon name="info" variant="inline" size="small" />
            This is a tooltip on the top
          </CmkTooltipContent>
        </CmkTooltip>
      </CmkTooltipProvider>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
