<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type CmkSpaceVariants } from '@/components/CmkSpace.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkButton from '@/components/CmkButton.vue'
${'import'} CmkSpace from '@/components/CmkSpace.vue'
<${'/'}script>

<template>
  <CmkButton variant="secondary">First Element</CmkButton>
  <CmkSpace direction="horizontal" size="medium" />
  <CmkButton variant="primary">Second Element</CmkButton>
</template>`
export const panelConfig = {
  direction: {
    type: 'list',
    title: 'Direction',
    options: [
      { title: 'Horizontal', name: 'horizontal' },
      { title: 'Vertical', name: 'vertical' }
    ] satisfies Options<CmkSpaceVariants['direction']>[],
    initialState: 'horizontal' as const
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' }
    ] satisfies Options<CmkSpaceVariants['size']>[],
    initialState: 'medium' as const
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

import CmkButton from '@/components/CmkButton.vue'
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSpace</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton variant="secondary">First Element</CmkButton>
      <CmkSpace :direction="propState.direction" :size="propState.size" />
      <CmkButton variant="primary">Second Element</CmkButton>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
