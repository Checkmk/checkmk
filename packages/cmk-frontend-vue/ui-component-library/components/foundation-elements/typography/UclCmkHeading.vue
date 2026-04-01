<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type HeadingType } from '@/components/typography/CmkHeading.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkHeading from '@/components/typography/CmkHeading.vue'
<${'/'}script>

<template>
  <CmkHeading type="h1">Main Title</CmkHeading>
  <CmkHeading type="h2" @click="console.log('Clicked!')">
    Make Clickable
  </CmkHeading>
</template>`
export const panelConfig = {
  type: {
    type: 'list',
    title: 'type',
    options: [
      { title: 'H1', name: 'h1' },
      { title: 'H2', name: 'h2' },
      { title: 'H3', name: 'h3' },
      { title: 'H4', name: 'h4' }
    ] satisfies Options<HeadingType>[],
    initialState: 'h1' as NonNullable<HeadingType>
  },
  text: {
    type: 'multiline-string',
    title: 'text',
    initialState: 'The quick brown fox jumps over the lazy dog.'
  },
  onClick: {
    type: 'boolean',
    title: 'onClick',
    initialState: false,
    help: 'When enabled, passes a click handler to the heading.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkHeading from '@/components/typography/CmkHeading.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))

function onHeadingClick() {
  alert('Heading clicked!')
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkHeading</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkHeading :type="propState.type" :on-click="propState.onClick ? onHeadingClick : null">
        {{ propState.text }}
      </CmkHeading>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
