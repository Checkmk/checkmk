<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type PieArcDatum, arc, pie } from 'd3-shape'
import { computed, ref, useId, watch } from 'vue'

import { chartColorCss } from '../colors'
import { DASH, formatDelta, noDelta } from '../format'
import DonutLegendCompact from './DonutLegendCompact.vue'
import DonutLegendTable from './DonutLegendTable.vue'
import type { CmkDonutChartProps, DonutLegendRow, DonutSlice } from './types'
import { type SliceAngles, useDonutTween } from './useDonutTween'

const { _t } = usei18n()
const props = withDefaults(defineProps<CmkDonutChartProps>(), { legendMode: 'table' })
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

// The eye column does not scale with the text; the value columns, the cell
// padding and a recognisable stretch of name do.
const COMPARISON_MIN_EM = 28
const COMPARISON_MIN_PX = 20
// Kept in step with --nf-donut-figure-min and --nf-donut-gap.
const RING_MIN_PX = 80
const GAP_EM = 0.75
const DEFAULT_FONT_SIZE_PX = 16

const rootRef = ref<HTMLElement | null>(null)
const width = ref(0)
const fontSize = ref(DEFAULT_FONT_SIZE_PX)

function measure(element: HTMLElement): void {
  width.value = element.getBoundingClientRect().width
  fontSize.value = Number.parseFloat(getComputedStyle(element).fontSize) || DEFAULT_FONT_SIZE_PX
}

const { observe } = useResizeObserver((entries) => {
  const entry = entries[0]
  if (entry?.target instanceof HTMLElement) {
    measure(entry.target)
  }
})
observe(rootRef)

// Ahead of the observer's first delivery, which arrives a frame late.
watch(
  rootRef,
  (element) => {
    if (element) {
      measure(element)
    }
  },
  { immediate: true }
)

const hasComparison = computed(() =>
  props.slices.some((slice) => slice.previousValue !== undefined)
)

// Measured against the width the legend has once the ring has given up
// everything it can, so the ring can then be sized off the answer. Nothing
// measured yet is not grounds for holding a column back.
const comparisonFits = computed(() => {
  if (width.value <= 0) {
    return true
  }
  const forLegend = width.value - RING_MIN_PX - GAP_EM * fontSize.value
  return forLegend >= COMPARISON_MIN_EM * fontSize.value + COMPARISON_MIN_PX
})

// Reserving the width of columns that carry no data would squeeze the ring for
// nothing, so the width the legend asks for follows both.
const showComparison = computed(() => hasComparison.value && comparisonFits.value)

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

// Every slice reports its activation and the caller decides what, if anything,
// opens: today only the remainder has a breakdown behind it. A collapsing slice
// is the exception, being on its way out of the ring rather than in it.
//
// Focused first, because a click does not focus an SVG group everywhere, and
// whatever this opens has to be able to hand the keyboard back.
function activate(segment: Segment, target: EventTarget | null): void {
  if (segment.leaving) {
    return
  }
  if (target instanceof SVGElement) {
    target.focus()
  }
  emit('sliceActivate', segment.key)
}

function percent(value: number): number {
  return total.value > 0 ? (value / total.value) * 100 : 0
}

function percentText(value: number): string {
  return `${percent(value).toFixed(1)}%`
}

// The reading that belongs to no slice. Prefixed, so a slice key cannot be it.
const TOTAL_CENTER_KEY = '__total__'

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
      // What the reading is about, so a handover can be told from a refresh
      // that leaves it saying the same thing.
      key: slice.key,
      label: slice.label,
      value: props.formatValue(slice.value),
      share: _t('%{share} of shown', { share: percentText(slice.value) })
    }
  }
  return {
    key: TOTAL_CENTER_KEY,
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

// The chart decides what the numbers are, down to what an absent one looks
// like, so the legend is left with no fallbacks of its own.
const legendRows = computed<DonutLegendRow[]>(() => {
  // Decided over the whole legend: a row without history in a legend that has
  // some still needs the two columns, filled with dashes.
  const anyPrevious = hasComparison.value
  return props.slices.map((slice) => {
    const isHidden = hidden.value.has(slice.key)
    const previous = slice.previousValue
    // A number measured over a ring it is not part of would be a fiction.
    const comparable = previous !== undefined && !isHidden
    return {
      key: slice.key,
      label: slice.label,
      color: slice.color,
      hidden: isHidden,
      isOther: slice.isOther ?? false,
      currentText: isHidden ? DASH : props.formatValue(slice.value),
      previousText: !anyPrevious ? null : comparable ? props.formatValue(previous) : DASH,
      delta: !anyPrevious ? null : comparable ? formatDelta(slice.value, previous) : noDelta()
    }
  })
})
</script>

<template>
  <div
    ref="rootRef"
    class="network-flow-cmk-donut-chart"
    :class="{
      'network-flow-cmk-donut-chart--compact': props.legendMode === 'compact',
      'network-flow-cmk-donut-chart--comparison': showComparison
    }"
  >
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
          @click="activate(segment, $event.currentTarget)"
          @keydown.enter.prevent="activate(segment, $event.currentTarget)"
          @keydown.space.prevent="activate(segment, $event.currentTarget)"
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
        <!-- Both readings are on screen while one takes over from the other,
             so they are stacked rather than played one after the next. -->
        <Transition name="network-flow-cmk-donut-chart__center-reading">
          <div :key="center.key" class="network-flow-cmk-donut-chart__center-reading">
            <span class="network-flow-cmk-donut-chart__center-label">{{ center.label }}</span>
            <span class="network-flow-cmk-donut-chart__center-value">{{ center.value }}</span>
            <span class="network-flow-cmk-donut-chart__center-share">{{ center.share }}</span>
          </div>
        </Transition>
      </div>
    </div>

    <DonutLegendCompact
      v-if="props.legendMode === 'compact'"
      :rows="legendRows"
      :highlighted="highlighted"
      @toggle="toggleHidden"
      @highlight="highlight"
      @drill="emit('sliceActivate', $event)"
    />
    <DonutLegendTable
      v-else
      :rows="legendRows"
      :previous-label="props.previousLabel"
      :show-comparison="showComparison"
      :highlighted="highlighted"
      @toggle="toggleHidden"
      @highlight="highlight"
      @drill="emit('sliceActivate', $event)"
    />
  </div>
</template>

<style>
@import url('../variables.css');
</style>

<style scoped>
.network-flow-cmk-donut-chart {
  /* What the legend needs before the ring is entitled to any width. Which of
     the two applies is decided in script, from the same numbers. */
  --nf-donut-legend-min: calc(16em + 20px);

  /* Past this the ring stops reading as a ring. */
  --nf-donut-figure-min: 80px;

  /* Not in cqw: this element is the container, so its own cq units would
     resolve against whatever box lies outside it. */
  --nf-donut-gap: 0.75em;

  /* The legend is served first and the ring takes what is left: a ring 100px
     across says what one 200px across says, a name clipped to "Un..." does not. */
  --nf-donut-figure-size: max(
    var(--nf-donut-figure-min),
    min(40cqw, 100cqh, calc(100cqw - var(--nf-donut-legend-min) - var(--nf-donut-gap)))
  );

  display: flex;
  gap: var(--nf-donut-gap);
  align-items: center;
  width: 100%;
  height: 100%;

  /* Height alone would leave a tall, narrow widget reading at its largest size
     in the least room. */
  font-size: clamp(11px, min(9cqh, 3.4cqw), 14px);

  /* Named, so the legend can ask about the widget rather than about whatever
     container happens to be nearest. */
  container: nf-donut / size;
}

/* Three more columns to make room for. */
.network-flow-cmk-donut-chart--comparison {
  --nf-donut-legend-min: calc(28em + 20px);
}

/* Stacked, the ring is bounded by the height it leaves the chips, so it
   competes with nothing for the width. */
.network-flow-cmk-donut-chart--compact {
  --nf-donut-figure-size: min(100cqw, 62cqh);

  flex-direction: column;
  justify-content: center;
}

.network-flow-cmk-donut-chart__figure {
  position: relative;
  flex: 0 0 auto;
  width: var(--nf-donut-figure-size);
  height: var(--nf-donut-figure-size);

  /* A container of its own, so what is written in the hole is measured against
     the ring rather than against the widget. */
  container-type: size;
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

  /* The hole is 73% of the figure across; the text stops short of its edge
     rather than reaching into the ring. */
  width: 70%;
  margin: 0 auto;
  font-size: clamp(7px, 8cqw, 16px);
  text-align: center;
}

/* Filling its box rather than flowing in it, so the outgoing reading is out of
   the layout and the incoming one does not start beneath it. */
.network-flow-cmk-donut-chart__center-reading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
  justify-content: center;
}

.network-flow-cmk-donut-chart__center-reading-enter-active,
.network-flow-cmk-donut-chart__center-reading-leave-active {
  transition: opacity 180ms ease-out;
}

.network-flow-cmk-donut-chart__center-reading-enter-from,
.network-flow-cmk-donut-chart__center-reading-leave-to {
  opacity: 0;
}

/* Long enough for the transition to still be one, short enough to read as the
   snap the reader asked for. */
@media (prefers-reduced-motion: reduce) {
  .network-flow-cmk-donut-chart__center-reading-enter-active,
  .network-flow-cmk-donut-chart__center-reading-leave-active {
    transition-duration: 1ms;
  }
}

.network-flow-cmk-donut-chart__center-value {
  max-width: 100%;
  overflow: hidden;
  font-size: 1.6em;
  font-weight: var(--font-weight-bold);
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
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
</style>
