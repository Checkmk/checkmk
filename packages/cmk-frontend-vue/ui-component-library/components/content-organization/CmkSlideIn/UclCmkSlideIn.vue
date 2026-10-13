<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type SlideInVariants } from 'cmk-ui-library/components/CmkSlideIn'

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
  open: { type: 'boolean' as const, title: 'Is Open', initialState: false },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<SlideInVariants['size']>({
      large: 'Large',
      medium: 'Medium',
      small: 'Small'
    }),
    initialState: 'medium' as const
  },
  ariaLabel: { type: 'string' as const, title: 'Aria Label', initialState: 'Demo Slide-In' },
  borderColor: {
    type: 'list' as const,
    title: 'Border Color',
    options: listOptions<SlideInVariants['borderColor']>({
      default: 'Default (green)',
      purple: 'Purple'
    }),
    initialState: 'default' as const
  }
} satisfies PanelConfigFor<typeof CmkSlideIn, 'stackPriority' | 'initialFocusTarget'>
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
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkSlideIn from 'cmk-ui-library/components/CmkSlideIn'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'

import UclCmkSlideInDev from './UclCmkSlideInDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkSlideIn,
  'stackPriority' | 'initialFocusTarget'
>().createRef(panelConfig)
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
        :border-color="propState.borderColor as SlideInVariants['borderColor']"
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
