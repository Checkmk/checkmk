<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type SlideInVariants } from '@/components/CmkSlideIn'

import codeExample from './UclCmkSlideInCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to container.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the focusable elements within the slide-in.'
  },
  {
    keys: ['Escape'],
    description: 'Automatically closes the slide-in.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'When the button is focused, pressing Enter or Space opens the slide-in.'
  },
  {
    keys: ['ArrowUp', 'ArrowDown'],
    description: 'Scrolls the content area line by line when it is focused and has overflow.'
  },
  {
    keys: ['PageUp', 'PageDown'],
    description:
      'Scrolls the content area up or down by a page when it is focused and has overflow.'
  },
  {
    keys: ['Home', 'End'],
    description:
      'Scrolls the content area to the top or bottom when it is focused and has overflow.'
  }
]

export const panelConfig = {
  open: { type: 'boolean', title: 'Is Open', initialState: false },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<SlideInVariants['size']>[],
    initialState: 'medium' as const
  },
  ariaLabel: { type: 'string', title: 'Aria Label', initialState: 'Demo Slide-In' }
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
import CmkSlideIn from '@/components/CmkSlideIn'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import UclCmkSlideInDev from './UclCmkSlideInDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSlideIn</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton @click="propState.open = true">Open Slide-In</CmkButton>

      <CmkSlideIn
        :open="propState.open"
        :size="propState.size"
        :aria-label="propState.ariaLabel"
        @close="propState.open = false"
      >
        <div
          style="
            padding: var(--dimension-5);
            display: flex;
            flex-direction: column;
            gap: var(--dimension-4);
            height: 100%;
          "
        >
          <CmkHeading type="h2">Slide-In Content</CmkHeading>

          <CmkParagraph>
            This is an overlay panel that slides in from the right. It traps focus and prevents
            interaction with the background page.
          </CmkParagraph>

          <CmkParagraph>
            Press <strong>Escape</strong> or click the <strong>Close</strong> button below (or the
            overlay backdrop) to dismiss it.
          </CmkParagraph>

          <div style="margin-top: auto">
            <CmkButton variant="primary" @click="propState.open = false">Close Panel</CmkButton>
          </div>
        </div>
      </CmkSlideIn>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkSlideInDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
