<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkPerfometerCodeExample.vue?raw'

const unlessSingleBar = (state: Record<string, unknown>): boolean => state['layout'] !== 'single'

export const panelConfig = {
  layout: {
    type: 'list' as const,
    title: 'Layout',
    help: 'A single bar is stated as value, valueRange and color. Everything the graphing layer draws from more than one run - a bar of several segments, two stacked bars, a bidirectional bar growing outwards from its centre - is passed as bars instead.',
    options: [
      { title: 'Single bar', name: 'single' },
      { title: 'Segmented bar', name: 'segmented' },
      { title: 'Stacked', name: 'stacked' },
      { title: 'Bidirectional', name: 'bidirectional' }
    ],
    initialState: 'single'
  },
  value: { type: 'number' as const, title: 'Value', initialState: 75, hiddenWhen: unlessSingleBar },
  valueRange: {
    type: 'string' as const,
    title: 'ValueRange',
    initialState: '0,100',
    help: 'Comma-separated min and max, e.g. "0,100"',
    hiddenWhen: unlessSingleBar
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
    initialState: 'green',
    hiddenWhen: unlessSingleBar
  }
} satisfies PanelConfigFor<typeof CmkPerfometer, 'bars'> & { layout: ListPropDef }
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
import CmkPerfometer, { type PerfometerSegment } from 'cmk-ui-library/components/CmkPerfometer.vue'
import { computed } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkPerfometer, 'bars'>().createRef(panelConfig)

const SAMPLES: Record<string, PerfometerSegment[][]> = {
  segmented: [
    [
      { share: 30, color: 'green' },
      { share: 25, color: 'blue' },
      { share: 45, color: null }
    ]
  ],
  stacked: [
    [
      { share: 70, color: 'green' },
      { share: 30, color: null }
    ],
    [
      { share: 35, color: 'orange' },
      { share: 65, color: null }
    ]
  ],
  bidirectional: [
    [
      { share: 25, color: null },
      { share: 25, color: 'blue' },
      { share: 12.5, color: 'orange' },
      { share: 37.5, color: null }
    ]
  ]
}

const bars = computed<PerfometerSegment[][] | undefined>(() => SAMPLES[propState.value.layout])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPerfometer</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkPerfometer
        :bars="bars"
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
