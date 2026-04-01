<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const a11yData: never[] = []
export const codeExample = `<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'
<${'/'}script>

<template>
  <CmkHtml html="<h1>Heading</h1> <b>bold</b> and <a href='https://checkmk.com'>link</a>" />
</template>`
export const panelConfig = {
  html: {
    type: 'multiline-string',
    title: 'html',
    initialState: "<h1>Heading</h1> <b>bold</b> and <a href='https://checkmk.com'>link</a>"
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

import CmkHtml from '@/components/CmkHtml.vue'

import UclCmkHtmlDev from './UclCmkHtmlDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkHtml</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkHtml :html="propState.html" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkHtmlDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
