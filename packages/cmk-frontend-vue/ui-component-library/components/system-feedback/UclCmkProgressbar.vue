<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type Sizes } from '@/components/CmkProgressbar.vue'

export const codeExample = `<script setup lang="ts">
${'import'} CmkProgressbar from '@/components/CmkProgressbar.vue'
<${'/'}script>

<template>
  <CmkProgressbar
    :value="30"
    :max="100"
    size="medium"
    :label="{ showTotal: true, unit: '%' }"
  />
</template>`
export const panelConfig = {
  value: { type: 'number', title: 'Current Value', initialState: 30 },
  max: {
    type: 'string',
    title: 'Max Value',
    initialState: '100',
    help: 'Leave empty for infinite mode'
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<NonNullable<Sizes>>[],
    initialState: 'medium' as const
  },
  label: { type: 'boolean', title: 'label', initialState: true }
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

import CmkProgressbar from '@/components/CmkProgressbar.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkProgressbar</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkProgressbar
        :value="propState.value"
        :max="propState.max ? Number(propState.max) : 'unknown'"
        :size="propState.size"
        :label="propState.label ? { showTotal: true, unit: '%' } : undefined"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
