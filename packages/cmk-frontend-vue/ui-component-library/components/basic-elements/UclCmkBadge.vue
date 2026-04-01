<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type Colors, type Shapes, type Sizes, type Types } from '@/components/CmkBadge.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkBadge from '@/components/CmkBadge.vue'
<${'/'}script>

<template>
  <CmkBadge
    color="danger"
    type="fill"
    shape="circle"
    size="medium"
  >
    99
  </CmkBadge>
</template>`
export const panelConfig = {
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
  type: {
    type: 'list',
    title: 'Type',
    options: [
      { title: 'Fill', name: 'fill' },
      { title: 'Outline', name: 'outline' }
    ] satisfies Options<Types>[],
    initialState: 'fill' as const
  },
  shape: {
    type: 'list',
    title: 'Shape',
    options: [
      { title: 'Default', name: 'default' },
      { title: 'Circle', name: 'circle' }
    ] satisfies Options<Shapes>[],
    initialState: 'default' as const
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

import CmkBadge from '@/components/CmkBadge.vue'

import UclCmkBadgeDev from './UclCmkBadgeDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkBadge</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkBadge
        :size="propState.size"
        :color="propState.color"
        :type="propState.type"
        :shape="propState.shape"
      >
        99
      </CmkBadge>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkBadgeDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
