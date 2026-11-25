<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { PanelConfig } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkFlyoutCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the trigger and, while open, through the popup content.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order; leaving the flyout entirely closes it.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Activates the focused trigger and opens the flyout.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the flyout and returns focus to the trigger.'
  }
]

export const panelConfig = {
  floating: {
    type: 'boolean',
    title: 'Floating',
    initialState: false,
    help: 'Position the popup relative to the window, so a scrolling container cannot cut it off. It opens below the trigger, or above it when only that side has room. Use it for flyouts inside scrolling areas such as tables.'
  }
} satisfies PanelConfig
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
import type { UserProps } from '@ucl/_ucl/types/prop-def'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkFlyout from 'cmk-ui-library/components/CmkFlyout'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { ref, useTemplateRef } from 'vue'

import UclCmkFlyoutDev from './UclCmkFlyoutDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkFlyout,
  keyof UserProps<typeof CmkFlyout>
>().createRef(panelConfig)

const open = ref(false)
const triggerRef = useTemplateRef<InstanceType<typeof CmkButton>>('triggerRef')
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkFlyout</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkFlyout
        :open="open"
        :label="untranslated('Toggle flyout')"
        :restore-focus="() => triggerRef?.focus()"
        :floating="propState.floating"
        @cancel="open = false"
      >
        <template #trigger="{ aria }">
          <CmkButton ref="triggerRef" v-bind="aria" @click="open = !open">Toggle flyout</CmkButton>
        </template>

        <p style="margin: 0">Any content can live inside the flyout popup.</p>
      </CmkFlyout>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkFlyoutDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
