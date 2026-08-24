<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { scaleLinear, scaleTime } from 'd3-scale'
import { area, curveCatmullRom, line } from 'd3-shape'
import { type Ref, computed, useId } from 'vue'

import type { KpiValueRange, TimestampedSample } from './types'

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

// The SVG is drawn in an abstract coordinate space and stretched to fit the
// card via preserveAspectRatio="none". D3 only generates the path strings here
// (Vue owns the DOM), so a fixed viewBox keeps the scaling math simple.
const VIEW_WIDTH = 100
const VIEW_HEIGHT = 40

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

const plot: Ref<Plot> = computed(() => {
  const data = props.series
  const values = data.filter((d) => d.value !== null).map((d) => d.value!)
  if (data.length < 2 || values.length < 2) {
    return EMPTY_PLOT
  }

  const xScale = scaleTime()
    .domain([
      new Date(data[0]!.timestamp * 1000),
      new Date(data[data.length - 1]!.timestamp * 1000)
    ])
    .range([0, VIEW_WIDTH])
  const x = (d: TimestampedSample) => xScale(new Date(d.timestamp * 1000))

  let domainMin: number
  let domainMax: number
  if (props.range) {
    domainMin = props.range.minimum
    domainMax = props.range.maximum
  } else {
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

  const ticks = props.range
    ? data
        .filter((d) => d.value !== null && (d.value! < domainMin || d.value! > domainMax))
        .map((d) => ({ x: x(d), y: y(d) }))
    : []

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
</script>

<template>
  <svg
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
</style>
