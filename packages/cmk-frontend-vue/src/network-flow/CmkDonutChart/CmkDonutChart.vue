<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type PieArcDatum, arc, pie } from 'd3-shape'
import { computed, useId } from 'vue'

import { chartColorCss } from '../colors'
import type { CmkDonutChartProps, DonutSlice } from './types'

const props = defineProps<CmkDonutChartProps>()

// The viewBox is centered on the origin, where d3 draws its arcs.
const SIZE = 300
const OUTER_RADIUS = 130
const INNER_RADIUS = 110
const TRACK_RADIUS = (OUTER_RADIUS + INNER_RADIUS) / 2
const TRACK_STROKE = OUTER_RADIUS - INNER_RADIUS
const SLICE_GAP_RADIANS = (1.5 * Math.PI) / 180

const sliceArc = arc<PieArcDatum<DonutSlice>>().innerRadius(INNER_RADIUS).outerRadius(OUTER_RADIUS)

// Unique per instance, or a second donut would reference this one's gradient.
const shadingId = `donut-shading-${useId()}`
// The gradient spans the full outer radius, so the ring's inner edge sits at
// this fraction of it.
const RING_INNER_OFFSET = `${(INNER_RADIUS / OUTER_RADIUS) * 100}%`

const total = computed(() => props.slices.reduce((sum, slice) => sum + slice.value, 0))

interface Segment {
  key: string
  color: string
  path: string
}

const segments = computed<Segment[]>(() => {
  if (total.value <= 0) {
    return []
  }
  const layout = pie<DonutSlice>()
    .sort(null)
    .value((slice) => slice.value)
    // A lone slice gets no gap: it would otherwise be a full ring with a notch
    // cut out of it.
    .padAngle(props.slices.length > 1 ? SLICE_GAP_RADIANS : 0)
  return layout(props.slices).map((datum) => ({
    key: datum.data.key,
    color: chartColorCss(datum.data.color),
    path: sliceArc(datum) ?? ''
  }))
})

function percent(value: number): number {
  return total.value > 0 ? (value / total.value) * 100 : 0
}

function percentText(value: number): string {
  return `${percent(value).toFixed(1)}%`
}

// The caller ranks the slices, so the top one is first.
const topSlice = computed(() => props.slices[0])
</script>

<template>
  <div class="network-flow-cmk-donut-chart">
    <div class="network-flow-cmk-donut-chart__figure">
      <svg
        class="network-flow-cmk-donut-chart__svg"
        :viewBox="`${-SIZE / 2} ${-SIZE / 2} ${SIZE} ${SIZE}`"
        role="img"
        preserveAspectRatio="xMidYMid meet"
      >
        <circle
          v-if="!segments.length"
          class="network-flow-cmk-donut-chart__empty-track"
          :r="TRACK_RADIUS"
          :stroke-width="TRACK_STROKE"
          fill="none"
        />
        <defs>
          <radialGradient
            :id="shadingId"
            gradientUnits="userSpaceOnUse"
            cx="0"
            cy="0"
            :r="OUTER_RADIUS"
          >
            <stop
              :offset="RING_INNER_OFFSET"
              class="network-flow-cmk-donut-chart__shading-stop--inner"
            />
            <stop offset="100%" class="network-flow-cmk-donut-chart__shading-stop--outer" />
          </radialGradient>
        </defs>
        <path
          v-for="segment in segments"
          :key="segment.key"
          class="network-flow-cmk-donut-chart__slice"
          :d="segment.path"
          :fill="segment.color"
        />
        <!-- Its own layer, so the slices keep their flat palette colour. -->
        <path
          v-for="segment in segments"
          :key="`${segment.key}-shading`"
          class="network-flow-cmk-donut-chart__shading"
          :d="segment.path"
          :fill="`url(#${shadingId})`"
        />
      </svg>
      <div v-if="topSlice" class="network-flow-cmk-donut-chart__center">
        <span class="network-flow-cmk-donut-chart__center-value">{{
          percentText(topSlice.value)
        }}</span>
        <span class="network-flow-cmk-donut-chart__center-label">{{ topSlice.label }}</span>
      </div>
    </div>

    <ul class="network-flow-cmk-donut-chart__legend">
      <li
        v-for="slice in slices"
        :key="slice.key"
        class="network-flow-cmk-donut-chart__legend-item"
      >
        <span
          class="network-flow-cmk-donut-chart__swatch"
          :style="{ backgroundColor: chartColorCss(slice.color) }"
        />
        <span class="network-flow-cmk-donut-chart__legend-label">{{ slice.label }}</span>
        <span class="network-flow-cmk-donut-chart__legend-value">{{
          percentText(slice.value)
        }}</span>
      </li>
    </ul>
  </div>
</template>

<style>
@import url('../variables.css');
</style>

<style scoped>
.network-flow-cmk-donut-chart {
  display: flex;
  gap: clamp(8px, 3cqw, 24px);
  align-items: center;
  width: 100%;
  height: 100%;
  font-size: clamp(11px, 9cqh, 14px);
  container-type: size;
}

.network-flow-cmk-donut-chart__figure {
  position: relative;
  flex: 0 0 auto;
  width: min(60cqw, 100cqh);
  height: min(60cqw, 100cqh);
}

.network-flow-cmk-donut-chart__svg {
  width: 100%;
  height: 100%;
}

/* The divider takes the colour of the surface behind the chart. */
.network-flow-cmk-donut-chart__slice {
  stroke: var(--db-content-bg-color);
  stroke-width: 1.5;
}

.network-flow-cmk-donut-chart__shading {
  pointer-events: none;
}

.network-flow-cmk-donut-chart__shading-stop--inner {
  stop-color: var(--nf-donut-shading-inner-color);
  stop-opacity: var(--nf-donut-shading-inner-opacity);
}

.network-flow-cmk-donut-chart__shading-stop--outer {
  stop-color: var(--nf-donut-shading-outer-color);
  stop-opacity: var(--nf-donut-shading-outer-opacity);
}

.network-flow-cmk-donut-chart__empty-track {
  stroke: var(--ux-theme-4);
}

.network-flow-cmk-donut-chart__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.network-flow-cmk-donut-chart__center-value {
  font-size: 1.6em;
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.network-flow-cmk-donut-chart__center-label {
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.network-flow-cmk-donut-chart__legend {
  flex: 1;
  min-width: 0;
  padding: 0;
  margin: 0;
  overflow: hidden;
  list-style: none;
}

.network-flow-cmk-donut-chart__legend-item {
  display: flex;
  gap: clamp(4px, 1cqw, 10px);
  align-items: center;
  padding: clamp(2px, 1.5cqh, 7px) 0;
  border-bottom: 1px solid var(--ux-theme-6);
}

.network-flow-cmk-donut-chart__swatch {
  flex: 0 0 auto;
  width: 0.75em;
  height: 0.75em;
  border-radius: 2px;
}

.network-flow-cmk-donut-chart__legend-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.network-flow-cmk-donut-chart__legend-value {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
