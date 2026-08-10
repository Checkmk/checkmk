<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { type PieArcDatum, arc, pie } from 'd3-shape'
import { computed, ref, useId } from 'vue'

import GraphLegendEyeButton from '@/graphing/components/legend/GraphLegendEyeButton.vue'

import { chartColorCss } from '../colors'
import type { CmkDonutChartProps, DonutSlice } from './types'
import { type SliceAngles, useDonutTween } from './useDonutTween'

const { _t } = usei18n()
const props = defineProps<CmkDonutChartProps>()
const emit = defineEmits<{ sliceActivate: [key: string] }>()

// The viewBox is centered on the origin, where d3 draws its arcs.
const SIZE = 300
const OUTER_RADIUS = 130
const INNER_RADIUS = 110
const TRACK_RADIUS = (OUTER_RADIUS + INNER_RADIUS) / 2
const TRACK_STROKE = OUTER_RADIUS - INNER_RADIUS
const SLICE_GAP_RADIANS = (1.5 * Math.PI) / 180
// Below this sweep the divider reads as a stray line, so it fades out.
const DIVIDER_FADE_RADIANS = (5 * Math.PI) / 180

const sliceArc = arc<PieArcDatum<DonutSlice>>().innerRadius(INNER_RADIUS).outerRadius(OUTER_RADIUS)

// Unique per instance, or a second donut would reference this one's gradient.
const shadingId = `donut-shading-${useId()}`
// The gradient spans the full outer radius, so the ring's inner edge sits at
// this fraction of it.
const RING_INNER_OFFSET = `${(INNER_RADIUS / OUTER_RADIUS) * 100}%`

// The ring, the total and every share are recomputed over what is left.
const hidden = ref(new Set<string>())

function toggleHidden(key: string): void {
  const next = new Set(hidden.value)
  if (!next.delete(key)) {
    next.add(key)
  }
  hidden.value = next
}

const visibleSlices = computed(() => props.slices.filter((slice) => !hidden.value.has(slice.key)))

// Counted off the slices at hand: a key hidden before its category left the
// data must not make the chart claim it is holding something back.
const hiddenCount = computed(() => props.slices.length - visibleSlices.value.length)

const total = computed(() => visibleSlices.value.reduce((sum, slice) => sum + slice.value, 0))

const targetAngles = computed<SliceAngles>(() => {
  // No traffic at all is no ring: the empty track takes over.
  if (total.value <= 0) {
    return new Map()
  }
  const layout = pie<DonutSlice>()
    .sort(null)
    .value((slice) => slice.value)
    // A lone slice gets no gap: it would otherwise be a full ring with a notch
    // cut out of it.
    .padAngle(visibleSlices.value.length > 1 ? SLICE_GAP_RADIANS : 0)
  return new Map(layout(visibleSlices.value).map((datum) => [datum.data.key, datum]))
})

const { angles: displayedAngles, leaving } = useDonutTween(targetAngles)

interface Segment {
  key: string
  label: string
  color: string
  path: string
  ariaLabel: string
  dividerOpacity: number
  leaving: boolean
}

// Driven by the tweened angles, because a leaving slice still has to be drawn.
const segments = computed<Segment[]>(() => {
  return [...displayedAngles.value.values()].map((datum) => ({
    key: datum.data.key,
    label: datum.data.label,
    color: chartColorCss(datum.data.color),
    path: sliceArc(datum) ?? '',
    ariaLabel: `${datum.data.label}, ${props.formatValue(datum.value)}, ${percentText(datum.value)}`,
    dividerOpacity: Math.min(1, (datum.endAngle - datum.startAngle) / DIVIDER_FADE_RADIANS),
    leaving: leaving.value.has(datum.data.key)
  }))
})

// A collapsing slice is on its way out of the ring: activating it would open
// the very category the reader just hid.
function activate(segment: Segment): void {
  if (!segment.leaving) {
    emit('sliceActivate', segment.key)
  }
}

function percent(value: number): number {
  return total.value > 0 ? (value / total.value) * 100 : 0
}

function percentText(value: number): string {
  return `${percent(value).toFixed(1)}%`
}

// One piece of state for ring, legend and center, so the highlight can be
// raised from either end.
const highlighted = ref<string | null>(null)

function highlight(key: string | null): void {
  highlighted.value = key
}

function isDimmed(key: string): boolean {
  // Pointing at a hidden category must not fade the whole ring.
  return highlightedSlice.value !== undefined && highlightedSlice.value.key !== key
}

const highlightedSlice = computed(() =>
  visibleSlices.value.find((slice) => slice.key === highlighted.value)
)

const center = computed(() => {
  const slice = highlightedSlice.value
  if (slice) {
    return {
      label: slice.label,
      value: props.formatValue(slice.value),
      share: _t('%{share} of shown', { share: percentText(slice.value) })
    }
  }
  return {
    label: props.centerLabel ?? _t('Volume'),
    value: props.formatValue(total.value),
    share:
      hiddenCount.value > 0
        ? _t('%{visible} of %{all} shown', {
            visible: `${visibleSlices.value.length}`,
            all: `${props.slices.length}`
          })
        : ''
  }
})
</script>

<template>
  <div class="network-flow-cmk-donut-chart">
    <div class="network-flow-cmk-donut-chart__figure">
      <svg
        class="network-flow-cmk-donut-chart__svg"
        :viewBox="`${-SIZE / 2} ${-SIZE / 2} ${SIZE} ${SIZE}`"
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
        <!-- Slice and shading share a group so that hovering, focusing and
             dimming address them as one shape. -->
        <!-- A leaving slice is out of reach: its share is measured against a
             ring it is on its way out of. -->
        <g
          v-for="segment in segments"
          :key="segment.key"
          class="network-flow-cmk-donut-chart__segment"
          :class="{
            'network-flow-cmk-donut-chart__segment--dimmed': isDimmed(segment.key),
            'network-flow-cmk-donut-chart__segment--leaving': segment.leaving
          }"
          role="button"
          :tabindex="segment.leaving ? -1 : 0"
          :aria-hidden="segment.leaving ? 'true' : undefined"
          :aria-label="segment.ariaLabel"
          @mouseenter="highlight(segment.key)"
          @mouseleave="highlight(null)"
          @focus="highlight(segment.key)"
          @blur="highlight(null)"
          @click="activate(segment)"
          @keydown.enter.prevent="activate(segment)"
          @keydown.space.prevent="activate(segment)"
        >
          <path
            class="network-flow-cmk-donut-chart__slice"
            :d="segment.path"
            :fill="segment.color"
            :stroke-opacity="segment.dividerOpacity"
          />
          <!-- Its own layer, so the slice keeps its flat palette colour. -->
          <path
            class="network-flow-cmk-donut-chart__shading"
            :d="segment.path"
            :fill="`url(#${shadingId})`"
          />
        </g>
      </svg>
      <div v-if="segments.length" class="network-flow-cmk-donut-chart__center">
        <span class="network-flow-cmk-donut-chart__center-label">{{ center.label }}</span>
        <span class="network-flow-cmk-donut-chart__center-value">{{ center.value }}</span>
        <span class="network-flow-cmk-donut-chart__center-share">{{ center.share }}</span>
      </div>
    </div>

    <ul class="network-flow-cmk-donut-chart__legend">
      <li
        v-for="slice in slices"
        :key="slice.key"
        class="network-flow-cmk-donut-chart__legend-item"
        :class="{
          'network-flow-cmk-donut-chart__legend-item--highlighted': highlighted === slice.key,
          'network-flow-cmk-donut-chart__legend-item--hidden': hidden.has(slice.key)
        }"
        @mouseenter="highlight(slice.key)"
        @mouseleave="highlight(null)"
      >
        <GraphLegendEyeButton
          :hidden="hidden.has(slice.key)"
          :aria-label="
            hidden.has(slice.key)
              ? _t('Show %{category} in the chart', { category: slice.label })
              : _t('Hide %{category} in the chart', { category: slice.label })
          "
          @toggle="toggleHidden(slice.key)"
        />
        <span
          class="network-flow-cmk-donut-chart__swatch"
          :style="{ backgroundColor: hidden.has(slice.key) ? '' : chartColorCss(slice.color) }"
        />
        <span class="network-flow-cmk-donut-chart__legend-label">{{ slice.label }}</span>
        <span class="network-flow-cmk-donut-chart__legend-value">{{
          hidden.has(slice.key) ? '–' : percentText(slice.value)
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

/* Capped at about a third of the width: past that it starves the legend. */
.network-flow-cmk-donut-chart__figure {
  position: relative;
  flex: 0 0 auto;
  width: min(40cqw, 100cqh);
  height: min(40cqw, 100cqh);
}

.network-flow-cmk-donut-chart__svg {
  width: 100%;
  height: 100%;
}

.network-flow-cmk-donut-chart__segment {
  cursor: pointer;
  transition:
    opacity 120ms,
    filter 120ms;
}

.network-flow-cmk-donut-chart__segment:hover,
.network-flow-cmk-donut-chart__segment:focus-visible {
  filter: drop-shadow(0 2px 5px var(--nf-donut-lift-shadow));
}

.network-flow-cmk-donut-chart__segment--dimmed {
  opacity: 0.5;
}

.network-flow-cmk-donut-chart__segment--leaving {
  pointer-events: none;
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

/* Covers the whole figure, so it has to let the pointer through. */
.network-flow-cmk-donut-chart__center {
  position: absolute;
  inset: 0;
  pointer-events: none;
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
  max-width: 100%;
  overflow: hidden;
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
  letter-spacing: 0.04em;
}

/* Kept in the layout even when empty, so the block does not jump. */
.network-flow-cmk-donut-chart__center-share {
  min-height: 1em;
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
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

.network-flow-cmk-donut-chart__legend-item--highlighted {
  background-color: var(--ux-theme-4);
}

/* A hidden category keeps its row, so it stays reachable. */
.network-flow-cmk-donut-chart__legend-item--hidden {
  opacity: 0.45;
}

.network-flow-cmk-donut-chart__swatch {
  flex: 0 0 auto;
  width: 0.75em;
  height: 0.75em;
  border-radius: 2px;
}

.network-flow-cmk-donut-chart__legend-item--hidden .network-flow-cmk-donut-chart__swatch {
  background-color: var(--color-mid-grey-30);
}

.network-flow-cmk-donut-chart__legend-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.network-flow-cmk-donut-chart__legend-value {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
