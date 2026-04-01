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
      'Moves focus sequentially to the scrollable code container, the "Show more/less" toggle button (if visible), and the Copy button. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse through the focusable elements.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Activates the "Show more/less" toggle or triggers the code copy action when the respective button is focused.'
  }
]
export const codeExample = `<script setup lang="ts">
${'import'} CmkCode from '@/components/CmkCode.vue'

const mySnippet = \`const greet = () => {
  console.log("Hello Checkmk!");
};
greet();\`
<${'/'}script>

<template>
  <CmkCode
    title="Greeting Function"
    :code_txt="mySnippet"
  />
</template>`
export const panelConfig = {
  title: {
    type: 'string',
    title: 'Title',
    initialState: 'Example Code Snippet'
  },
  code_txt: {
    type: 'multiline-string',
    title: 'Code Text',
    initialState: `<script setup lang="ts">
${'import'} CmkCode from '@/components/CmkCode.vue'

const mySnippet = \`const greet = () => {
  console.log("Hello Checkmk!");
};
greet();\`
<${'/'}script>

<template>
  <CmkCode
    title="Greeting Function"
    :code_txt="mySnippet"
  />
</template>`
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
import { ref } from 'vue'

import CmkCode from '@/components/CmkCode.vue'

import UclCmkCodeDev from './UclCmkCodeDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCode</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCode :title="propState.title" :code_txt="propState.code_txt" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCodeDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
