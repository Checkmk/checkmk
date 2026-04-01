<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type CmkIconVariants, type IconSizeNames, type SimpleIcons } from '@/components/CmkIcon'

export const codeExample = `<script setup lang="ts">
${'import'} CmkIcon from '@/components/CmkIcon'
<${'/'}script>

<template>
  <CmkIcon
    name="main-help"
    size="large"
    variant="inline"
    title="Get Help"
  />
</template>`
export const panelConfig = {
  name: { type: 'string', title: 'Icon Name', initialState: 'main-help' },
  variant: {
    type: 'list',
    title: 'Variant',
    options: [
      { title: 'Plain', name: 'plain' },
      { title: 'Inline (with margin)', name: 'inline' }
    ],
    initialState: 'plain'
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'XX-Small', name: 'xxsmall' },
      { title: 'X-Small', name: 'xsmall' },
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'X-Large', name: 'xlarge' },
      { title: 'XX-Large', name: 'xxlarge' },
      { title: 'XXX-Large', name: 'xxxlarge' }
    ],
    initialState: 'xxlarge'
  },
  colored: { type: 'boolean', title: 'Colored', initialState: false },
  title: { type: 'string', title: 'Title (Tooltip/Alt)', initialState: 'Help Icon' },
  rotate: { type: 'number', title: 'Rotation (Degrees)', initialState: 0 }
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

import CmkIcon from '@/components/CmkIcon'

import UclCmkIconDev from './UclCmkIconDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIcon</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIcon
        :name="propState.name as SimpleIcons"
        :variant="propState.variant as CmkIconVariants['variant']"
        :size="propState.size as IconSizeNames"
        :colored="propState.colored"
        :title="propState.title"
        :rotate="propState.rotate"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkIconDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
