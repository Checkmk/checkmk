<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkPerfometerCodeExample.vue?raw'

export const panelConfig = {
  value: { type: 'number' as const, title: 'Value', initialState: 75 },
  valueRange: {
    type: 'string' as const,
    title: 'ValueRange',
    initialState: '0,100',
    help: 'Comma-separated min and max, e.g. "0,100"'
  },
  formatted: { type: 'string' as const, title: 'Formatted', initialState: '75 %' },
  color: {
    type: 'list' as const,
    title: 'Color',
    options: [
      { title: 'Green', name: 'green' },
      { title: 'Orange', name: 'orange' },
      { title: 'Red', name: 'red' },
      { title: 'Blue', name: 'blue' }
    ],
    initialState: 'green'
  }
} satisfies PanelConfigFor<typeof CmkPerfometer>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'

import CmkPerfometer from '@/components/CmkPerfometer.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkPerfometer>().createRef(panelConfig)
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
