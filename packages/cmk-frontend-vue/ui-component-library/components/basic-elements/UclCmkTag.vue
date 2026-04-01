<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type Colors, type Sizes, type Variants } from '@/components/CmkTag.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkTag from '@/components/CmkTag.vue'
<${'/'}script>

<template>
  <CmkTag
    content="Critical Issue"
    color="default"
    variant="outline"
    size="medium"
  />
</template>`
export const panelConfig = {
  content: {
    type: 'string',
    title: 'Content',
    initialState: 'Status Tag'
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<Sizes>[],
    initialState: 'medium' as const
  },
  color: {
    type: 'list',
    title: 'Color',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' }
    ] satisfies Options<Colors>[],
    initialState: 'default' as const
  },
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Outline', name: 'outline' },
      { title: 'Fill', name: 'fill' }
    ] satisfies Options<Variants>[],
    initialState: 'outline' as const
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

import CmkTag from '@/components/CmkTag.vue'

import UclCmkTagDev from './UclCmkTagDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTag</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTag
        :content="propState.content"
        :size="propState.size"
        :color="propState.color"
        :variant="propState.variant"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkTagDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
