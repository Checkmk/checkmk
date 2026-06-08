<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
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
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import { ref, useTemplateRef } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkButton from '@/components/CmkButton'
import CmkFlyout from '@/components/CmkFlyout'

import UclCmkFlyoutDev from './UclCmkFlyoutDev.vue'

defineProps<{ screenshotMode: boolean }>()

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
        @cancel="open = false"
      >
        <template #trigger="{ aria }">
          <CmkButton ref="triggerRef" v-bind="aria" @click="open = !open">Toggle flyout</CmkButton>
        </template>

        <p style="margin: 0">Any content can live inside the flyout popup.</p>
      </CmkFlyout>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkFlyoutDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
