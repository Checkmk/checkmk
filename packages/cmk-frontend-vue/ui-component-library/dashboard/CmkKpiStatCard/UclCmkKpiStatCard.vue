<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import { type DeltaSemantics, type KpiStateSeverity } from '@/dashboard/components/CmkKpiStatCard'

import codeExample from './UclCmkKpiStatCardCodeExample.vue?raw'

export const panelConfig = {
  value: {
    type: 'string' as const,
    title: 'Value',
    help: 'Pre-formatted headline value. The card never formats, it only displays.',
    initialState: '801.84'
  },
  unit: {
    type: 'string' as const,
    title: 'Unit',
    help: 'Rendered smaller after the value. Leave empty for plain counts.',
    initialState: 'GB'
  },
  color: {
    type: 'list' as const,
    title: 'Accent color',
    help: 'CSS color of the value and the spark line.',
    options: [
      { title: 'Blue', name: 'var(--color-light-blue-50)' },
      { title: 'Green', name: 'var(--color-corporate-green-50)' },
      { title: 'Grey', name: 'var(--color-mid-grey-50)' },
      { title: 'Magenta', name: 'var(--color-pink-50)' },
      { title: 'Orange', name: 'var(--color-orange-50)' },
      { title: 'Purple', name: 'var(--color-purple-50)' },
      { title: 'Red', name: 'var(--color-light-red-50)' },
      { title: 'Yellow', name: 'var(--color-yellow-50)' }
    ],
    initialState: 'var(--color-corporate-green-50)' as const
  },
  showDelta: {
    type: 'boolean' as const,
    title: 'Show delta',
    help: 'Renders the change versus the previous period. Without it the indicator is omitted entirely.',
    initialState: true
  },
  deltaPercent: {
    type: 'number' as const,
    title: 'Delta (%)',
    help: 'Signed change versus the previous period. Negative values point the arrow down.',
    initialState: 6.2
  },
  deltaSemantics: {
    type: 'list' as const,
    title: 'Delta semantics',
    help: 'What an increase means. Neutral stays grey; on a "bad" metric an increase renders red, on a "good" one green.',
    options: [
      { title: 'Neutral', name: 'neutral' },
      { title: 'Good', name: 'good' },
      { title: 'Bad', name: 'bad' }
    ] satisfies Options<DeltaSemantics>[],
    initialState: 'neutral' as const
  },
  pointCount: {
    type: 'number' as const,
    title: 'Spark line points',
    help: 'Points taken from the sample series. Fewer than two draw no line at all.',
    initialState: 30
  },
  showState: {
    type: 'boolean' as const,
    title: 'Show state',
    help: 'Renders the monitoring state of whatever the value was measured on, as a badge beside it.',
    initialState: false
  },
  stateSeverity: {
    type: 'list' as const,
    title: 'State',
    options: [
      { title: 'OK', name: 'ok' },
      { title: 'WARN', name: 'warn' },
      { title: 'CRIT', name: 'crit' },
      { title: 'UNKN', name: 'unknown' },
      { title: 'PEND', name: 'pending' }
    ] satisfies Options<KpiStateSeverity>[],
    initialState: 'warn' as const
  },
  tintBackground: {
    type: 'boolean' as const,
    title: 'Tint background',
    help: 'Colors the whole card in the state color. Needs a state to be shown.',
    initialState: false
  },
  showRangeLimits: {
    type: 'boolean' as const,
    title: 'Show range limits',
    help: 'Labels both ends of the displayed value range over the spark line.',
    initialState: false
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked value',
    help: 'Turns the value into a link, e.g. into the service view it was read from.',
    initialState: false
  },
  containerWidth: {
    type: 'number' as const,
    title: 'Card width (px)',
    help: 'The card scales its text to its box, so its size is what the preview varies.',
    initialState: 280
  },
  containerHeight: {
    type: 'number' as const,
    title: 'Card height (px)',
    initialState: 130
  }
} satisfies PanelConfigFor<
  typeof CmkKpiStatCard,
  'series' | 'state' | 'rangeLimits' | 'deltaRatio' | 'href'
> & {
  showDelta: BoolPropDef
  deltaPercent: NumberPropDef
  pointCount: NumberPropDef
  showState: BoolPropDef
  stateSeverity: ListPropDef<KpiStateSeverity>
  tintBackground: BoolPropDef
  showRangeLimits: BoolPropDef
  linked: BoolPropDef
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

import CmkKpiStatCard, {
  type KpiRangeLimits,
  type KpiState
} from '@/dashboard/components/CmkKpiStatCard'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkKpiStatCard,
  'series' | 'state' | 'rangeLimits' | 'deltaRatio' | 'href'
>().createRef(panelConfig)

// A window of per-minute values, oldest first (as the compute endpoints
// deliver them).
const SERIES = [
  62, 68, 75, 71, 66, 73, 82, 78, 74, 80, 88, 92, 85, 79, 83, 90, 95, 89, 84, 91, 97, 94, 87, 93,
  99, 96, 90, 95, 101, 98
]

const series = computed(() => SERIES.slice(0, Math.max(0, propState.value.pointCount)))

const state = computed<KpiState | undefined>(() =>
  propState.value.showState
    ? {
        severity: propState.value.stateSeverity,
        tintBackground: propState.value.tintBackground
      }
    : undefined
)

const rangeLimits = computed<KpiRangeLimits | undefined>(() =>
  propState.value.showRangeLimits ? { minimum: '0 B', maximum: '1.00 TB' } : undefined
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkKpiStatCard</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        class="ucl-cmk-kpi-stat-card__container"
        :style="{
          width: `${Math.max(0, propState.containerWidth)}px`,
          height: `${Math.max(0, propState.containerHeight)}px`
        }"
      >
        <CmkKpiStatCard
          :value="propState.value"
          :unit="propState.unit || undefined"
          :delta-ratio="propState.showDelta ? propState.deltaPercent / 100 : undefined"
          :delta-semantics="propState.deltaSemantics"
          :series="series"
          :color="propState.color"
          :state="state"
          :range-limits="rangeLimits"
          :href="propState.linked ? '#' : undefined"
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
/* The card fills whatever box it is given and scales its text to it, so the
   preview provides an explicitly sized one. */
.ucl-cmk-kpi-stat-card__container {
  resize: both;
  overflow: hidden;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
