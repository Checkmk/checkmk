<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import { type Sizes, type Variants } from '@/components/CmkAlertBox.vue'

import codeExample from './UclCmkAlertBoxCodeExample.vue?raw'

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
    keys: ['Enter', 'Space'],
    description: 'Activates the focused action or dismissal button within the dialog.'
  }
]

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Open', initialState: true },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Info', name: 'info' },
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Error', name: 'error' },
      { title: 'Loading', name: 'loading' }
    ] satisfies Options<NonNullable<Variants>>[],
    initialState: 'info' as const
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<NonNullable<Sizes>>[],
    initialState: 'medium' as const
  },
  heading: { type: 'string' as const, title: 'Heading', initialState: 'Alert Heading' },
  dismissible: {
    type: 'boolean' as const,
    title: 'Dismissible',
    initialState: false,
    help: 'Only available for info and success variants. Only has effect when no buttons are enabled.'
  },
  autoDismiss: { type: 'boolean' as const, title: 'Auto Dismiss (6s)', initialState: false },
  mainButton: { type: 'boolean' as const, title: 'Main Button', initialState: false },
  optionalButton: { type: 'boolean' as const, title: 'Optional Button', initialState: false }
} satisfies PanelConfigFor<typeof CmkAlertBox>
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

import CmkAlertBox, { type CmkAlertBoxProps } from '@/components/CmkAlertBox.vue'

import UclCmkAlertBoxDev from './UclCmkAlertBoxDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkAlertBox>().createRef(panelConfig)

const alertBoxProps = computed(
  () =>
    ({
      open: propState.value.open,
      variant: propState.value.variant,
      size: propState.value.size,
      heading: propState.value.heading,
      autoDismiss: propState.value.autoDismiss,
      dismissible: propState.value.dismissible,
      ...(propState.value.mainButton && {
        mainButton: { title: 'Confirm', onclick: () => console.log('Confirm clicked') }
      }),
      ...(propState.value.optionalButton && {
        optionalButton: {
          title: 'Dismiss',
          icon: 'cancel' as const,
          onclick: () => console.log('Dismiss clicked')
        }
      })
    }) as CmkAlertBoxProps & { open: boolean }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAlertBox</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAlertBox v-bind="alertBoxProps" v-model:open="propState.open">
        This is a demonstration of the alert box content. You can put any long text or HTML elements
        in here to showcase wrapping and layout.
      </CmkAlertBox>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkAlertBoxDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
