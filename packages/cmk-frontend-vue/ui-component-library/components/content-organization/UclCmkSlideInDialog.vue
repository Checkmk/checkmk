<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type CmkIconProps } from '@/components/CmkIcon'

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
    description: 'Scrolls the content area when it is focused and has overflow.'
  }
]
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
${'import'} CmkButton from '@/components/CmkButton.vue'

const isOpen = ref(false)
<${'/'}script>

<template>
  <CmkButton @click="isOpen = true">Open Dialog</CmkButton>

  <CmkSlideInDialog
    :open="isOpen"
    :header="{
      title: 'Dialog Title',
      closeButton: true,
      icon: { name: 'info-circle', size: 'medium' }
    }"
    @close="isOpen = false"
  >
    <p>This dialog comes with a built-in header and scroll container.</p>
    <CmkButton variant="primary" @click="isOpen = false">Confirm Action</CmkButton>
  </CmkSlideInDialog>
</template>`

type DialogSize = 'medium' | 'small'

export const panelConfig = {
  open: { type: 'boolean', title: 'Is Open', initialState: false },
  title: { type: 'string', title: 'Header Title', initialState: 'Dialog Title' },
  showCloseButton: { type: 'boolean', title: 'Show Close Button', initialState: true },
  showIcon: { type: 'boolean', title: 'Show Header Icon', initialState: true },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<DialogSize>[],
    initialState: 'medium' as const
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
import { computed, ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import UclCmkSlideInDialogDev from './UclCmkSlideInDialogDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

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
