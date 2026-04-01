<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type ButtonVariants } from '@/components/CmkButton.vue'
import { type DismissalButtonKey } from '@/components/CmkDialog.vue'

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
export const codeExample = `<script setup lang="ts">
${'import'} CmkDialog from '@/components/CmkDialog.vue'

function handleAction() {
  console.log('Action triggered')
}
<${'/'}script>

<template>
  <CmkDialog
    variant="info"
    title="Dialog Title"
    message="This is an informational message that requires user attention."
    :buttons="[
      { title: 'Acknowledge', variant: 'info', onclick: handleAction }
    ]"
    :dismissal_button="{ title: 'Dismiss', key: 'immediate_slideout_change' }"
  />
</template>`

type DialogVariant = 'info' | 'error' | 'success' | 'warning' | 'loading'

export const panelConfig = {
  variant: {
    type: 'list',
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
  title: { type: 'string', title: 'Title', initialState: 'Dialog Title' },
  message: {
    type: 'string',
    title: 'Message',
    initialState: 'This is a sample message demonstrating the dialog content and layout.'
  },
  buttons: { type: 'boolean', title: 'Buttons', initialState: true },
  dismissal_button: { type: 'boolean', title: 'Dismissal Button', initialState: false }
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

import CmkDialog from '@/components/CmkDialog.vue'

import UclCmkDialogDev from './UclCmkDialogDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

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
  ...(propState.value.dismissal_button && {
    dismissal_button: {
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
