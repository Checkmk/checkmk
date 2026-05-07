<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExampleButton from './UclCmkCopyButtonCodeExample.vue?raw'
import codeExample from './UclCmkCopyCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus through the Copy button. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the Copy button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Triggers the copy action and opens the confirmation tooltip, assuming an interactive element (like a button) is provided in the default slot.'
  },
  {
    keys: ['Escape'],
    description: 'Dismisses the active tooltip if it is currently visible.'
  }
]

export const panelConfig = {
  text: { type: 'string' as const, title: 'Text to Copy', initialState: 'cmk --check myhost' },
  copiedMessage: { type: 'string' as const, title: 'Copied Message', initialState: 'Copied!' }
} satisfies PanelConfigFor<typeof CmkCopy>
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

import CmkButton from '@/components/CmkButton'
import CmkCopy from '@/components/CmkCopy.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'

import UclCmkCopyDev from './UclCmkCopyDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkCopy>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCopyIcon (Icon)</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCopy :text="propState.text">
        <CmkIconButton name="copied" size="medium" title="Copy" />
      </CmkCopy>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageHeader>CmkCopyIcon (Button)</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCopy :text="propState.text">
        <CmkButton variant="secondary">Copy</CmkButton>
      </CmkCopy>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExampleButton" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCopyDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
