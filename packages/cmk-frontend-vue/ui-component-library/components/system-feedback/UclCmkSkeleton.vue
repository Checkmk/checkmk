<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type SkeletonType } from '@/components/CmkSkeleton.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkSkeleton from '@/components/CmkSkeleton.vue'
<${'/'}script>

<template>
  <div class="user-card-loading">
    <CmkSkeleton type="icon-xlarge" />
    <div class="user-card-text">
      <CmkSkeleton type="h3" width="60%" />
      <CmkSkeleton type="info-text" width="40%" />
    </div>
  </div>
</template>`
export const panelConfig = {
  type: {
    type: 'list',
    title: 'Skeleton Type',
    options: [
      { title: 'Box', name: 'box' },
      { title: 'H1', name: 'h1' },
      { title: 'H2', name: 'h2' },
      { title: 'H3', name: 'h3' },
      { title: 'Text', name: 'text' },
      { title: 'Info Text', name: 'info-text' },
      { title: 'Icon: X-Small', name: 'icon-xsmall' },
      { title: 'Icon: Small', name: 'icon-small' },
      { title: 'Icon: Medium', name: 'icon-medium' },
      { title: 'Icon: Large', name: 'icon-large' },
      { title: 'Icon: X-Large', name: 'icon-xlarge' },
      { title: 'Icon: XX-Large', name: 'icon-xxlarge' },
      { title: 'Icon: XXX-Large', name: 'icon-xxxlarge' }
    ] satisfies Options<NonNullable<SkeletonType>>[],
    initialState: 'text' as const
  },
  width: {
    type: 'string',
    title: 'Custom Width',
    help: 'Optionally set a custom width for the skeleton using any valid CSS unit(% or px).',
    initialState: '100%'
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

import CmkSkeleton from '@/components/CmkSkeleton.vue'

import UclCmkSkeletonDev from './UclCmkSkeletonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSkeleton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkSkeleton :type="propState.type" :width="propState.width" />
      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkSkeletonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
