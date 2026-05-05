<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import { type ButtonVariants } from '@/components/CmkButton'
import type { DismissalButtonKey } from '@/components/CmkDialog.vue'

import codeExample from './UclCmkDialogCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the button. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the interactive elements within the dialog.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the dialog.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused action or dismissal button within the dialog.'
  }
]

type DialogVariant = 'info' | 'error' | 'success' | 'warning' | 'loading'

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Info', name: 'info' },
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Error', name: 'error' },
      { title: 'Loading', name: 'loading' }
    ] satisfies Options<DialogVariant>[],
    initialState: 'info' as DialogVariant
  },
  title: { type: 'string' as const, title: 'Title', initialState: 'Dialog Title' },
  message: {
    type: 'string' as const,
    title: 'Message',
    initialState: 'This is a sample message demonstrating the dialog content and layout.'
  },
  buttons: { type: 'boolean' as const, title: 'Buttons', initialState: true },
  dismissalButton: { type: 'boolean' as const, title: 'Dismissal Button', initialState: false }
} satisfies PanelConfigFor<typeof CmkDialog>
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
import { computed } from 'vue'

import CmkDialog from '@/components/CmkDialog.vue'

import UclCmkDialogDev from './UclCmkDialogDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkDialog>().createRef(panelConfig)

const dialogProps = computed(() => ({
  variant: propState.value.variant,
  title: propState.value.title,
  message: propState.value.message,
  ...(propState.value.buttons && {
    buttons: [
      {
        title: 'Action Button',
        variant: (propState.value.variant === 'error'
          ? 'danger'
          : propState.value.variant === 'loading'
            ? 'success'
            : propState.value.variant) as ButtonVariants['variant'],
        onclick: () => console.log('Action button clicked')
      }
    ]
  }),
  ...(propState.value.dismissalButton && {
    dismissalButton: {
      title: 'Dismiss',
      key: 'immediate_slideout_change' as DismissalButtonKey
    }
  })
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDialog</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDialog v-bind="dialogProps" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkDialogDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
