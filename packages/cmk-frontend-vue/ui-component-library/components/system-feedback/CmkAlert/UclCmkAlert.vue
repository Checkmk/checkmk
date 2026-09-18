<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { type Sizes, type Variants } from 'cmk-ui-library/components/CmkAlert.vue'

import codeExample from './UclCmkAlertCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus through the buttons and the close button in reading order.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the interactive elements within the box.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused action or the close button.'
  }
]

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Open', initialState: true },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<NonNullable<Variants>>({
      info: 'Info',
      success: 'Success',
      warning: 'Warning',
      error: 'Error',
      loading: 'Loading'
    }),
    initialState: 'info' as const
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<NonNullable<Sizes>>({
      medium: 'Medium',
      small: 'Small'
    }),
    initialState: 'medium' as const,
    help: 'Small is a single line without heading or buttons; long text is cut off and shown on hover.'
  },
  heading: {
    type: 'string' as const,
    title: 'Heading',
    initialState: 'Alert Heading',
    help: 'Medium size only.'
  },
  text: {
    type: 'string' as const,
    title: 'Text',
    initialState: 'This is the alert text. It provides context for the user.'
  },
  dismissible: {
    type: 'boolean' as const,
    title: 'Dismissible',
    initialState: false,
    help: 'Only available for info and success variants. Only has effect when no buttons are enabled.'
  },
  autoDismiss: { type: 'boolean' as const, title: 'Auto Dismiss (6s)', initialState: false },
  mainButton: {
    type: 'boolean' as const,
    title: 'Main Button',
    initialState: false,
    help: 'Medium size only.'
  },
  optionalButton: {
    type: 'boolean' as const,
    title: 'Optional Button',
    initialState: false,
    help: 'Medium size only.'
  }
} satisfies PanelConfigFor<typeof CmkAlert>
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
import CmkAlert, { type CmkAlertProps } from 'cmk-ui-library/components/CmkAlert.vue'
import { computed } from 'vue'

import UclCmkAlertDev from './UclCmkAlertDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkAlert>().createRef(panelConfig)

const alertBoxProps = computed(() => {
  const state = propState.value
  const message = {
    variant: state.variant,
    text: state.text,
    autoDismiss: state.autoDismiss,
    dismissible: state.dismissible
  }
  if (state.size === 'small') {
    return { ...message, size: 'small' } as CmkAlertProps
  }
  return {
    ...message,
    size: 'medium',
    heading: state.heading,
    ...(state.mainButton && {
      mainButton: { title: 'Confirm', onclick: () => console.log('Confirm clicked') }
    }),
    ...(state.optionalButton && {
      optionalButton: {
        title: 'Dismiss',
        icon: 'cancel' as const,
        onclick: () => console.log('Dismiss clicked')
      }
    })
  } as CmkAlertProps
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAlert</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkAlert v-bind="alertBoxProps" v-model:open="propState.open" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkAlertDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
