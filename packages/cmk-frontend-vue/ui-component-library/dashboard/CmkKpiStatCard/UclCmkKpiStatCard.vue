<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import {
  type ComparisonBasis,
  type KpiStateSeverity,
  type SparkHeightMode
} from '@/dashboard/components/CmkKpiStatCard'

import codeExample from './UclCmkKpiStatCardCodeExample.vue?raw'

/** Demo-only: which missing-data scenario the series generator produces. */
type DataState = 'complete' | 'gap' | 'stale' | 'no-data'

export const panelConfig = {
  title: {
    type: 'string' as const,
    title: 'Title',
    help: 'Read as part of the composite aria-label a scrubbable card exposes on focus.',
    initialState: 'Total bytes'
  },
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
    help: 'CSS color of the value and the spark line. Only used when no state is shown - a shown state always colors them instead.',
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
    initialState: 'var(--color-corporate-green-50)' as const,
    hiddenWhen: (s) => s.colorMode === 'state'
  },
  showDelta: {
    type: 'boolean' as const,
    title: 'Show delta',
    help: 'Renders the change versus the comparison basis. Without it the indicator is omitted entirely.',
    initialState: true
  },
  comparisonBasis: {
    type: 'list' as const,
    title: 'Comparison basis',
    help: 'What the delta compares the current value against, computed over the real samples before it.',
    options: listOptions<ComparisonBasis>({
      average: 'Average',
      last: 'Last sample',
      minimum: 'Minimum',
      maximum: 'Maximum',
      median: 'Median'
    }),
    initialState: 'average' as const
  },
  sparkHeightMode: {
    type: 'list' as const,
    title: 'Spark line height',
    help: 'Band reserves the lower part of the card so the curve and the numbers never overlap. Full runs the curve behind the numbers, behind a card-colored scrim.',
    options: listOptions<SparkHeightMode>({
      band: 'Band',
      full: 'Full'
    }),
    initialState: 'band' as const
  },
  pointCount: {
    type: 'number' as const,
    title: 'Spark line points',
    help: 'Points taken from the sample series. Fewer than two draw no line at all, which is also what omitting the series does.',
    initialState: 30
  },
  dataState: {
    type: 'list' as const,
    title: 'Data state',
    help: 'Gap: a single contiguous outage window mid-series. Stale: the series ends in missing samples, so the bridge runs flat to the right edge and the delta is replaced by a "last sample" note. No data: no value, curve, delta, or state badge at all.',
    options: listOptions<DataState>({
      complete: 'Complete',
      gap: 'Gap',
      stale: 'Stale',
      'no-data': 'No data'
    }),
    initialState: 'complete' as const
  },
  colorMode: {
    type: 'list' as const,
    title: 'Display mode',
    help: 'Color: the value and spark line use the accent color. State: they follow the monitoring state instead, shown as a badge beside the value.',
    options: listOptions<'color' | 'state'>({
      color: 'Color',
      state: 'State'
    }),
    initialState: 'color' as const
  },
  stateSeverity: {
    type: 'list' as const,
    title: 'State',
    options: listOptions<KpiStateSeverity>({
      ok: 'OK',
      warn: 'WARN',
      crit: 'CRIT',
      unknown: 'UNKN',
      pending: 'PEND'
    }),
    initialState: 'warn' as const,
    hiddenWhen: (s) => s.colorMode === 'color'
  },
  tintBackground: {
    type: 'boolean' as const,
    title: 'Tint background',
    help: 'Colors the whole card in the state color too, not just the value and spark line.',
    initialState: false,
    hiddenWhen: (s) => s.colorMode === 'color'
  },
  showRangeLimits: {
    type: 'boolean' as const,
    title: 'Show range limits',
    help: 'Labels both ends of the displayed value range over the spark line.',
    initialState: false
  },
  manualRange: {
    type: 'boolean' as const,
    title: 'Manual vertical scale',
    help: 'Fixes the spark line scale to Range min/max instead of auto-padding to the data. Samples outside it clamp to the edge and get a tick.',
    initialState: false
  },
  rangeMin: {
    type: 'number' as const,
    title: 'Range min',
    initialState: 70
  },
  rangeMax: {
    type: 'number' as const,
    title: 'Range max',
    initialState: 90
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
    initialState: 560
  },
  containerHeight: {
    type: 'number' as const,
    title: 'Card height (px)',
    initialState: 260
  }
} satisfies PanelConfigFor<
  typeof CmkKpiStatCard,
  'series' | 'state' | 'stale' | 'rangeLimits' | 'range' | 'href' | 'formatValue' | 'delta'
> & {
  sparkHeightMode: ListPropDef<SparkHeightMode>
  showDelta: BoolPropDef
  comparisonBasis: ListPropDef<ComparisonBasis>
  pointCount: NumberPropDef
  dataState: ListPropDef<DataState>
  colorMode: ListPropDef<'color' | 'state'>
  stateSeverity: ListPropDef<KpiStateSeverity>
  tintBackground: BoolPropDef
  showRangeLimits: BoolPropDef
  manualRange: BoolPropDef
  rangeMin: NumberPropDef
  rangeMax: NumberPropDef
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
  type KpiState,
  type KpiValueRange,
  type TimestampedSample
} from '@/dashboard/components/CmkKpiStatCard'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkKpiStatCard,
  'series' | 'state' | 'stale' | 'rangeLimits' | 'range' | 'href' | 'formatValue' | 'delta'
>().createRef(panelConfig)

// A window of per-minute values, oldest first (as the compute endpoints
// deliver them), one minute apart.
const SERIES_VALUES = [
  62, 68, 75, 71, 66, 73, 82, 78, 74, 80, 88, 92, 85, 79, 83, 90, 95, 89, 84, 91, 97, 94, 87, 93,
  99, 96, 90, 95, 101, 98
]
const SERIES: TimestampedSample[] = SERIES_VALUES.map((value, index) => ({
  timestamp: index * 60,
  value
}))

const series = computed<TimestampedSample[]>(() => {
  const sliced = SERIES.slice(0, Math.max(0, propState.value.pointCount))
  const dataState = propState.value.dataState
  if (dataState === 'gap') {
    // One contiguous outage window, roughly a third in - a single real gap to bridge.
    const gapStart = Math.floor(sliced.length * 0.33)
    const gapLength = Math.max(2, Math.floor(sliced.length * 0.15))
    return sliced.map((point, index) =>
      index >= gapStart && index < gapStart + gapLength ? { ...point, value: null } : point
    )
  }
  if (dataState === 'stale') {
    // A trailing run of missing samples, not a gap bounded by real data on both sides.
    const staleFrom = Math.max(0, sliced.length - Math.max(2, Math.floor(sliced.length * 0.15)))
    return sliced.map((point, index) => (index >= staleFrom ? { ...point, value: null } : point))
  }
  return sliced
})

const state = computed<KpiState | undefined>(() =>
  propState.value.colorMode === 'state'
    ? {
        severity: propState.value.stateSeverity,
        tintBackground: propState.value.tintBackground
      }
    : undefined
)

const rangeLimits = computed<KpiRangeLimits | undefined>(() =>
  propState.value.showRangeLimits ? { minimum: '0 B', maximum: '1.00 TB' } : undefined
)

const range = computed<KpiValueRange | undefined>(() =>
  propState.value.manualRange
    ? { minimum: propState.value.rangeMin, maximum: propState.value.rangeMax }
    : undefined
)

// Series values are unitless demo numbers, so the comparison basis text just
// appends whatever unit is currently configured for the headline value.
function formatValue(value: number): string {
  const unit = propState.value.unit
  return unit ? `${value.toFixed(1)} ${unit}` : value.toFixed(1)
}
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
          :title="propState.title"
          :value="propState.dataState === 'no-data' ? undefined : propState.value"
          :unit="propState.unit || undefined"
          :delta="{ show: propState.showDelta, comparisonBasis: propState.comparisonBasis }"
          :format-value="formatValue"
          :series="series"
          :color="propState.color"
          :state="state"
          :range-limits="rangeLimits"
          :range="range"
          :spark-height-mode="propState.sparkHeightMode"
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
