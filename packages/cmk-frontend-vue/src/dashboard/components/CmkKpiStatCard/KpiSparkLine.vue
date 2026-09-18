<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type ScaleTime, scaleLinear, scaleTime } from 'd3-scale'
import { area, curveCatmullRom, line } from 'd3-shape'
import { type Ref, computed, ref, useId, watchEffect } from 'vue'

import type { KpiValueRange, TimestampedSample } from './types'
import { nearestRealSampleIndex, useKpiSparkLineFocus } from './useKpiSparkLineHover'

const props = withDefaults(
  defineProps<{
    /** Data points to plot, oldest first. Needs at least two non-null values to render a path. */
    series: TimestampedSample[]
    /** Stroke / fill color, e.g. "var(--color-corporate-green-50)". */
    color: string
    /** Fades the area fill towards the floor instead of the default flat fill. */
    fadeToFloor?: boolean
    /** Fixed vertical scale bounds. Omit for the default: automatic, padded to the data. */
    range?: KpiValueRange | undefined
  }>(),
  { fadeToFloor: false, range: undefined }
)

/**
 * `xPercent` lets the parent draw its own full-card crosshair line: in band
 * mode this SVG only covers the area below the value/date text, so a line
 * confined to it could never reach "top to bottom of the widget".
 */
const emit = defineEmits<{
  focus: [sample: TimestampedSample | undefined, xPercent: number | undefined]
}>()

// The SVG is drawn in an abstract coordinate space and stretched to fit the
// card via preserveAspectRatio="none". D3 only generates the path strings here
// (Vue owns the DOM), so a fixed viewBox keeps the scaling math simple.
const VIEW_WIDTH = 100
const VIEW_HEIGHT = 40

// A non-scaling stroke (dot, crosshair) on a viewBox edge gets clipped, so the x-scale
// renders into this narrower range, shifting the whole plot to stay aligned with it.
const X_INSET = 3

// Unique per instance so multiple cards on one dashboard don't share <defs> ids.
const instanceId = useId()
const fadeMaskId = `db-kpi-spark-line-fade-mask-${instanceId}`
const fadeGradientId = `db-kpi-spark-line-fade-gradient-${instanceId}`
const floorGradientId = `db-kpi-spark-line-floor-gradient-${instanceId}`
const hatchPatternId = `db-kpi-spark-line-hatch-${instanceId}`

interface Point {
  x: number
  y: number
}

/** A dashed bridge across a run of missing samples, with a hatched fill beneath it. */
interface Bridge {
  line: string
  area: string
}

interface Plot {
  line: string
  area: string
  /** Marks the latest non-null sample; null when there is nothing to plot. */
  dot: Point | null
  /** One per sample clamped into a manual range. */
  ticks: Point[]
  /** One bridge per gap, plus a flat trailing bridge if the series ends in missing samples (stale). */
  bridges: Bridge[]
}

const EMPTY_PLOT: Plot = { line: '', area: '', dot: null, ticks: [], bridges: [] }

interface Scales {
  x: (d: TimestampedSample) => number
  y: (d: TimestampedSample) => number
  /** The raw time scale, kept for .invert() - pointer hover needs pixel-to-timestamp, not just the other way. */
  xScale: ScaleTime<number, number>
  /** Every non-null sample, oldest first - what hover/keyboard scrubbing steps through. */
  realSamples: TimestampedSample[]
  domainMin: number
  domainMax: number
}

// Split out from `plot` so hover/keyboard scrubbing doesn't rebuild the same
// domain-padding math for just the scales.
const scales = computed<Scales | null>(() => {
  const data = props.series
  const realSamples = data.filter((d) => d.value !== null)
  if (data.length < 2 || realSamples.length < 2) {
    return null
  }

  const xScale = scaleTime()
    .domain([
      new Date(data[0]!.timestamp * 1000),
      new Date(data[data.length - 1]!.timestamp * 1000)
    ])
    .range([X_INSET, VIEW_WIDTH - X_INSET])
  const x = (d: TimestampedSample) => xScale(new Date(d.timestamp * 1000))

  let domainMin: number
  let domainMax: number
  if (props.range) {
    domainMin = props.range.minimum
    domainMax = props.range.maximum
  } else {
    const values = realSamples.map((d) => d.value!)
    const min = Math.min(...values)
    const max = Math.max(...values)
    // Pad the value range so the line never touches the very top/bottom edge.
    const padding = (max - min) * 0.15 || 1
    domainMin = min - padding
    domainMax = max + padding
  }
  const yScale = scaleLinear().domain([domainMin, domainMax]).range([VIEW_HEIGHT, 0])
  const clampToRange = (value: number) => Math.min(domainMax, Math.max(domainMin, value))
  const y = (d: TimestampedSample) => yScale(clampToRange(d.value!))

  return { x, y, xScale, realSamples, domainMin, domainMax }
})

const plot: Ref<Plot> = computed(() => {
  const data = props.series
  const resolved = scales.value
  if (!resolved) {
    return EMPTY_PLOT
  }
  const { x, y, domainMin, domainMax } = resolved

  // .defined() splits the solid curve at each missing run; a dashed, hatched
  // bridge (gap, or a stale tail at the end) is drawn across it below.
  const lineGen = line<TimestampedSample>()
    .defined((d) => d.value !== null)
    .x(x)
    .y(y)
    .curve(curveCatmullRom.alpha(0.5))

  const areaGen = area<TimestampedSample>()
    .defined((d) => d.value !== null)
    .x(x)
    .y0(VIEW_HEIGHT)
    .y1(y)
    .curve(curveCatmullRom.alpha(0.5))

  const latest = [...data].reverse().find((d) => d.value !== null)
  const dot = latest ? { x: x(latest), y: y(latest) } : null

  // One tick per excursion, not per sample - a long run of out-of-range samples (e.g.
  // idling below a manual floor for many minutes) would otherwise draw a tick for each
  // one, a dense comb instead of a single marker at the excursion's start.
  const ticks: Point[] = []
  if (props.range) {
    let wasOutOfRange = false
    for (const d of data) {
      const isOutOfRange = d.value !== null && (d.value < domainMin || d.value > domainMax)
      if (isOutOfRange && !wasOutOfRange) {
        ticks.push({ x: x(d), y: y(d) })
      }
      wasOutOfRange = isOutOfRange
    }
  }

  const bridgeLineGen = line<TimestampedSample>().x(x).y(y)
  const bridgeAreaGen = area<TimestampedSample>().x(x).y0(VIEW_HEIGHT).y1(y)

  const bridges: Bridge[] = []
  let lastRealIndex = -1
  for (let i = 0; i < data.length; i++) {
    if (data[i]!.value === null) {
      continue
    }
    if (lastRealIndex !== -1 && i > lastRealIndex + 1) {
      const pair = [data[lastRealIndex]!, data[i]!]
      bridges.push({ line: bridgeLineGen(pair) ?? '', area: bridgeAreaGen(pair) ?? '' })
    }
    lastRealIndex = i
  }
  // A trailing run has no "after" point, so the bridge runs flat to the right
  // edge instead: a synthetic sample at the series' own last timestamp (which
  // x() maps to VIEW_WIDTH) carries the last real value forward.
  if (lastRealIndex !== -1 && lastRealIndex < data.length - 1) {
    const flatEnd: TimestampedSample = {
      timestamp: data[data.length - 1]!.timestamp,
      value: data[lastRealIndex]!.value
    }
    const pair = [data[lastRealIndex]!, flatEnd]
    bridges.push({ line: bridgeLineGen(pair) ?? '', area: bridgeAreaGen(pair) ?? '' })
  }

  return { line: lineGen(data) ?? '', area: areaGen(data) ?? '', dot, ticks, bridges }
})

const realSamples = computed(() => scales.value?.realSamples ?? [])
const focus = useKpiSparkLineFocus(realSamples)

const svgEl = ref<SVGSVGElement | null>(null)

const crosshair = computed(() => {
  const resolved = scales.value
  const sample = focus.focusedSample.value
  if (!resolved || !sample) {
    return null
  }
  return { x: resolved.x(sample), y: resolved.y(sample) }
})

watchEffect(() => {
  emit(
    'focus',
    focus.focusedSample.value,
    crosshair.value ? (crosshair.value.x / VIEW_WIDTH) * 100 : undefined
  )
})

// Exposed for the parent to drive: the parent owns pointer events (scrubbing spans
// the whole card, not just this SVG); only the coordinate math lives here.
function focusFromPointerX(clientX: number): void {
  const resolved = scales.value
  const svg = svgEl.value
  if (!resolved || !svg) {
    return
  }
  const rect = svg.getBoundingClientRect()
  if (rect.width === 0) {
    return
  }
  const viewBoxX = ((clientX - rect.left) / rect.width) * VIEW_WIDTH
  const targetTimestamp = resolved.xScale.invert(viewBoxX).getTime() / 1000
  focus.setIndex(nearestRealSampleIndex(resolved.realSamples, targetTimestamp))
}

defineExpose({
  focusFromPointerX,
  stepBy: focus.stepBy,
  jumpToStart: focus.jumpToStart,
  jumpToEnd: focus.jumpToEnd,
  jumpToPeak: focus.jumpToPeak,
  jumpToLow: focus.jumpToLow,
  clear: focus.clearImmediately,
  clearWithDelay: focus.clearWithDelay,
  isHoverable: computed(() => scales.value !== null),
  focusedIndex: focus.focusedIndex,
  sampleCount: computed(() => realSamples.value.length)
})
</script>

<template>
  <svg
    ref="svgEl"
    class="db-kpi-spark-line"
    :viewBox="`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`"
    preserveAspectRatio="none"
    :style="{ color }"
    aria-hidden="true"
  >
    <defs>
      <!-- Fades stroke and fill together towards the past: 50% opacity at the
           oldest sample to full at the latest, independent of whichever fill
           treatment (flat or fade-to-floor) the area below uses. -->
      <linearGradient :id="fadeGradientId" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="white" stop-opacity="0.5" />
        <stop offset="100%" stop-color="white" stop-opacity="1" />
      </linearGradient>
      <mask :id="fadeMaskId">
        <rect
          x="0"
          y="0"
          :width="VIEW_WIDTH"
          :height="VIEW_HEIGHT"
          :fill="`url(#${fadeGradientId})`"
        />
      </mask>
      <linearGradient v-if="fadeToFloor" :id="floorGradientId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
        <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
      </linearGradient>
      <!-- Diagonal stripes for the area under a gap or stale-tail bridge, so a missing run
           reads as "no data here" rather than a plain (and easily missed) blank patch. -->
      <pattern
        :id="hatchPatternId"
        width="1.5"
        height="1.5"
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"
      >
        <line x1="0" y1="0" x2="0" y2="1.5" stroke="currentColor" stroke-opacity="0.45" />
      </pattern>
    </defs>
    <g :mask="`url(#${fadeMaskId})`">
      <path
        v-for="(bridge, index) in plot.bridges"
        :key="`bridge-area-${index}`"
        class="db-kpi-spark-line__bridge-area"
        :d="bridge.area"
        :fill="`url(#${hatchPatternId})`"
        stroke="none"
      />
      <path
        class="db-kpi-spark-line__area"
        :d="plot.area"
        :fill="fadeToFloor ? `url(#${floorGradientId})` : 'currentColor'"
        :fill-opacity="fadeToFloor ? undefined : 0.35"
        stroke="none"
      />
      <path
        v-for="(bridge, index) in plot.bridges"
        :key="`bridge-line-${index}`"
        class="db-kpi-spark-line__bridge-line"
        :d="bridge.line"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-dasharray="1 2.5"
        vector-effect="non-scaling-stroke"
      />
      <path
        class="db-kpi-spark-line__line"
        :d="plot.line"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        vector-effect="non-scaling-stroke"
      />
      <path
        v-if="plot.dot"
        class="db-kpi-spark-line__dot"
        :d="`M ${plot.dot.x},${plot.dot.y} L ${plot.dot.x},${plot.dot.y}`"
        stroke="currentColor"
        stroke-width="6"
        stroke-linecap="round"
        vector-effect="non-scaling-stroke"
        fill="none"
      />
      <path
        v-for="(tick, index) in plot.ticks"
        :key="index"
        class="db-kpi-spark-line__tick"
        :d="
          tick.y === 0
            ? `M ${tick.x},0 L ${tick.x},6`
            : `M ${tick.x},${tick.y - 6} L ${tick.x},${VIEW_HEIGHT}`
        "
        stroke="currentColor"
        stroke-width="1.5"
        vector-effect="non-scaling-stroke"
        fill="none"
      />
    </g>
    <!-- Outside the fade mask so the dot's opacity isn't doubled by the mask's own fade. The
         crosshair line itself is drawn by the parent card - in band mode this SVG doesn't
         reach the widget's top. -->
    <Transition name="db-kpi-spark-line__crosshair">
      <g v-if="crosshair" class="db-kpi-spark-line__crosshair">
        <!-- Zero-length round-capped lines, not <circle>s: preserveAspectRatio="none"
             stretches a circle's radius non-uniformly into an ellipse, but a
             non-scaling stroke stays a fixed-diameter dot regardless (same
             technique as the latest-sample dot above). A wider white line
             behind the curve-colored one reads as a ring around it, matching
             the graphing initiative's own pointer dot. -->
        <path
          :d="`M ${crosshair.x},${crosshair.y} L ${crosshair.x},${crosshair.y}`"
          stroke="white"
          stroke-width="8"
          stroke-linecap="round"
          vector-effect="non-scaling-stroke"
          fill="none"
        />
        <path
          :d="`M ${crosshair.x},${crosshair.y} L ${crosshair.x},${crosshair.y}`"
          stroke="currentColor"
          stroke-width="6"
          stroke-linecap="round"
          vector-effect="non-scaling-stroke"
          fill="none"
        />
      </g>
    </Transition>
  </svg>
</template>

<style scoped>
.db-kpi-spark-line {
  display: block;
  width: 100%;

  /* Stops short of the bottom edge, so the card keeps a visible floor. A real
     pixel value, not a viewBox unit: preserveAspectRatio="none" stretches the
     viewBox non-uniformly, so a fixed number of viewBox units would only ever
     equal 8px at one specific card height. */
  height: calc(100% - 8px);
}

.db-kpi-spark-line__crosshair-enter-active,
.db-kpi-spark-line__crosshair-leave-active {
  transition: opacity 120ms linear;
}

.db-kpi-spark-line__crosshair-enter-from,
.db-kpi-spark-line__crosshair-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .db-kpi-spark-line__crosshair-enter-active,
  .db-kpi-spark-line__crosshair-leave-active {
    transition: none;
  }
}
</style>
