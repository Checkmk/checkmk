<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const codeExample = `<script setup lang="ts">
${'import'} CmkPerfometer from '@/components/CmkPerfometer.vue'
<${'/'}script>

<template>
  <CmkPerfometer
    :value="75"
    :value-range="[0, 100]"
    formatted="75 %"
    color="green"
  />
</template>`
export const panelConfig = {
  value: { type: 'number', title: 'Value', initialState: 75 },
  valueRange: {
    type: 'string',
    title: 'ValueRange',
    initialState: '0,100',
    help: 'Comma-separated min and max, e.g. "0,100"'
  },
  formatted: { type: 'string', title: 'Formatted', initialState: '75 %' },
  color: {
    type: 'list',
    title: 'Color',
    options: [
      { title: 'Green', name: 'green' },
      { title: 'Orange', name: 'orange' },
      { title: 'Red', name: 'red' },
      { title: 'Blue', name: 'blue' }
    ],
    initialState: 'green'
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

import CmkPerfometer from '@/components/CmkPerfometer.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPerfometer</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkPerfometer
        :value="propState.value"
        :value-range="(propState.valueRange as string).split(',').map(Number) as [number, number]"
        :formatted="propState.formatted"
        :color="propState.color"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
