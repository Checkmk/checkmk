<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, StringPropDef } from '@ucl/_ucl/types/prop-def'
import { type CmkIconProps } from 'cmk-ui-library/components/CmkIcon'
import type { SlideInVariants } from 'cmk-ui-library/components/CmkSlideIn'
import type { CmkSlideInDialogProps } from 'cmk-ui-library/components/CmkSlideInDialog.vue'

import codeExample from './UclCmkSlideInDialogCodeExample.vue?raw'

type OmittedProps = 'stackPriority' | 'header' | 'initialFocusTarget'
type CmkSlideInDialogDemoProps = PanelConfigFor<typeof CmkSlideInDialog, OmittedProps> & {
  title: StringPropDef
  showCloseButton: BoolPropDef
  showIcon: BoolPropDef
}

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus through the focusable elements within the dialog.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the focusable elements within the dialog.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the dialog.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused action button within the dialog.'
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
  title: { type: 'string' as const, title: 'Header Title', initialState: 'Dialog Title' },
  showCloseButton: { type: 'boolean' as const, title: 'Show Close Button', initialState: true },
  showIcon: { type: 'boolean' as const, title: 'Show Header Icon', initialState: true },
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
  borderColor: {
    type: 'list' as const,
    title: 'Border Color',
    options: listOptions<SlideInVariants['borderColor']>({
      default: 'Default',
      purple: 'Purple'
    }),
    initialState: 'default' as const
  },
  spacing: {
    type: 'list' as const,
    title: 'Spacing',
    options: listOptions<CmkSlideInDialogProps['spacing']>({
      default: 'Default',
      wide: 'Wide'
    }),
    initialState: 'default' as const
  }
} satisfies CmkSlideInDialogDemoProps
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
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { computed } from 'vue'

import UclCmkSlideInDialogDev from './UclCmkSlideInDialogDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSlideInDialog, OmittedProps>().createRef(
  panelConfig
)

const headerConfig = computed(() => ({
  title: propState.value.title,
  closeButton: propState.value.showCloseButton,
  icon: propState.value.showIcon
    ? ({ name: 'info-circle', size: 'medium' } as CmkIconProps)
    : undefined
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSlideInDialog</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton @click="propState.open = true">Open Dialog</CmkButton>

      <CmkSlideInDialog
        :open="propState.open"
        :header="headerConfig"
        :size="propState.size"
        :border-color="propState.borderColor"
        :spacing="propState.spacing"
        @close="propState.open = false"
      >
        <CmkHeading type="h2">Content Area</CmkHeading>
        <CmkParagraph>
          This dialog comes with a built-in header and scroll container.
        </CmkParagraph>

        <div style="margin-top: var(--dimension-4)">
          <CmkButton variant="primary" @click="propState.open = false"> Confirm Action </CmkButton>
        </div>
      </CmkSlideInDialog>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkSlideInDialogDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
