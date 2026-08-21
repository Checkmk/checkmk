<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import type { DonutLegendMode } from '@/network-flow/CmkDonutChart'

export const panelConfig = {
  legendMode: {
    type: 'list' as const,
    title: 'Legend',
    help: 'The table states the volume per category. The chips name the categories only and stack under the ring, for widgets with no width for both.',
    options: [
      { title: 'Table', name: 'table' },
      { title: 'Compact', name: 'compact' }
    ] satisfies Options<DonutLegendMode>[],
    initialState: 'table' as const
  },
  centerLabel: {
    type: 'string' as const,
    title: 'Center label',
    help: 'Captions the total in the middle of the ring. Defaults to "Volume".',
    initialState: 'Volume'
  },
  categories: {
    type: 'number' as const,
    title: 'Categories',
    help: 'How many of the sample categories to rank, before the aggregated remainder.',
    initialState: 5
  },
  showOther: {
    type: 'boolean' as const,
    title: 'Aggregated remainder',
    help: 'Appends the "Other" slice. It is the one row drawn as drillable, with a chevron.',
    initialState: true
  },
  previousPeriod: {
    type: 'boolean' as const,
    title: 'Previous period',
    help: 'Gives every category a previous value, which is what makes the Previous and Change columns appear. They drop out again once the widget is too narrow for three numbers per row.',
    initialState: false
  },
  containerWidth: {
    type: 'number' as const,
    title: 'Widget width (px)',
    help: 'The chart sizes itself to its box, so its size is what the preview varies. The tightest widget a dashboard allows is 320 x 180.',
    initialState: 560
  },
  containerHeight: {
    type: 'number' as const,
    title: 'Widget height (px)',
    initialState: 260
  }
} satisfies PanelConfigFor<typeof CmkDonutChart, 'slices' | 'formatValue'> & {
  categories: NumberPropDef
  showOther: BoolPropDef
  previousPeriod: BoolPropDef
  containerWidth: NumberPropDef
  containerHeight: NumberPropDef
}
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
import { computed } from 'vue'

import CmkDonutChart, { type DonutSlice } from '@/network-flow/CmkDonutChart'
import { formatBytes } from '@/network-flow/format'

import codeExample from './UclCmkDonutChartCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkDonutChart, 'slices' | 'formatValue'>().createRef(
  panelConfig
)

// Ranked, as the widget receives them, and long enough to show a name giving way.
const CATEGORIES: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 4_720_000_000, color: 'blue' },
  { key: 'pops', label: 'POPS', value: 1_700_000_000, color: 'purple' },
  { key: 'imaps', label: 'IMAPS', value: 1_100_000_000, color: 'cyan' },
  { key: 'smtps', label: 'SMTPS', value: 900_000_000, color: 'magenta' },
  { key: 'unknown', label: 'Unknown application', value: 760_000_000, color: 'orange' },
  { key: 'dns', label: 'DNS', value: 240_000_000, color: 'brown' }
]

// Made up per category rather than by one factor, so growth, decline and
// growth out of nothing are all on screen at once.
const PREVIOUS_FACTORS = [0.8, 1.35, 1, 0.45, 0, 1.9]

const slices = computed<DonutSlice[]>(() => {
  const ranked = CATEGORIES.slice(0, Math.max(1, Math.min(propState.value.categories, 6))).map(
    (slice, index) => ({
      ...slice,
      ...(propState.value.previousPeriod
        ? { previousValue: slice.value * PREVIOUS_FACTORS[index]! }
        : {})
    })
  )
  if (!propState.value.showOther) {
    return ranked
  }
  const other = 820_000_000
  return [
    ...ranked,
    {
      key: 'other',
      label: 'Other',
      value: other,
      color: 'grey' as const,
      isOther: true,
      ...(propState.value.previousPeriod ? { previousValue: other * 1.1 } : {})
    }
  ]
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDonutChart</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        class="ucl-cmk-donut-chart__container"
        :style="{
          width: `${Math.max(0, propState.containerWidth)}px`,
          height: `${Math.max(0, propState.containerHeight)}px`
        }"
      >
        <CmkDonutChart
          :slices="slices"
          :format-value="formatBytes"
          :center-label="propState.centerLabel"
          :legend-mode="propState.legendMode"
        />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
/* Bordered and resizable: the chart fills whatever box it is given, so the box
   is what has to be visible. */
.ucl-cmk-donut-chart__container {
  overflow: hidden;
  resize: both;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
