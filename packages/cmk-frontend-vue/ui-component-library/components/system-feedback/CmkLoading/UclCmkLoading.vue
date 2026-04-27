<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const codeExample = `<script setup lang="ts">
${'import'} CmkLoading from '@/components/CmkLoading.vue'
<${'/'}script>

<template>
  <CmkLoading height="8px" />
</template>`
export const panelConfig = {
  height: {
    type: 'string',
    title: 'Dot Height',
    help: 'Adjust the height of the loading dots using any valid CSS unit (e.g., px, em, rem). 8px is default and recommended for most use cases.',
    initialState: '8px'
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

import CmkLoading from '@/components/CmkLoading.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkLoading</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        style="
          min-height: 80px;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
        "
      >
        <CmkLoading :height="propState.height" />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
