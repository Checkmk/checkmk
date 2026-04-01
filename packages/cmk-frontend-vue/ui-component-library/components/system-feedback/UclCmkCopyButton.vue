<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

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
export const codeExample = `<script setup lang="ts">
${'import'} CmkButton from '@/components/CmkButton.vue'
${'import'} CmkCopy from '@/components/CmkCopy.vue'
<${'/'}script>

<template>
  <CmkCopy text="cmk --check myhost">
    <CmkButton variant="secondary">Copy</CmkButton>
  </CmkCopy>
</template>`
export const panelConfig = {
  text: { type: 'string', title: 'Text to Copy', initialState: 'cmk --check myhost' }
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
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkCopy from '@/components/CmkCopy.vue'

import UclCmkCopyDev from './UclCmkCopyDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCopyButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <code>{{ propState.text }}</code>

      <CmkCopy :text="propState.text">
        <CmkButton variant="secondary">Copy</CmkButton>
      </CmkCopy>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCopyDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
