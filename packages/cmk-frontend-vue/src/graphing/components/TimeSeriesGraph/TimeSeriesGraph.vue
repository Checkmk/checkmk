<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { scaleLinear, scaleTime } from 'd3-scale'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { userSpecificUnit } from '@/lib/unit-format/unitFormatter'

import { computeTimeAxis } from './axes/timeAxis'
import { computeYDomain } from './axes/valueAxis'
import { downsampleToColumns, m4 } from './decimation/decimate'
import type { M4Cache } from './decimation/types'
import { drawData } from './render'
import { invertBucket } from './render/bucket'
import { drawHorizontalLines } from './render/horizontalLines'
import { computeStackedSeries } from './render/stacked'
import type { ConsolidationFn, TimeSeriesGraphProps } from './types'
import { useAxes } from './useAxes'

const props = defineProps<TimeSeriesGraphProps>()

const consolidationFn = computed<ConsolidationFn>(() => props.consolidationFunction ?? 'avg')

const MARGIN = { top: 5, right: 10, bottom: 24, left: 50 } as const
// Top/bottom canvas padding so lines at the domain min/max are not clipped.
const CANVAS_Y_PADDING = 4
// Bucket count for the M4 cache built on receive (4000 is the default, consider changing
// if necessary).
const M4_BUCKETS = 4000

const canvas = ref<HTMLCanvasElement | null>(null)
const axesContainer = ref<SVGGElement | null>(null)

const plotWidth = computed(() => props.size.width)
const plotHeight = computed(() => props.size.height)
const figureWidth = computed(() => plotWidth.value + MARGIN.left + MARGIN.right)
const figureHeight = computed(() => plotHeight.value + MARGIN.top + MARGIN.bottom)

// 'iec' notation is 1024-based so its ticks step in binary; every other notation is decimal.
const yStepping = computed((): 'binary' | 'decimal' =>
  props.options.y_axis?.unit.notation === 'iec' ? 'binary' : 'decimal'
)
const yTickFormatter = computed((): ((value: number) => string) => {
  const unit = props.options.y_axis?.unit
  if (!unit) {
    return (value: number) => String(value)
  }
  const { formatter } = userSpecificUnit(unit, 'celsius')
  return (value: number) => formatter.render(value)
})

const xScale = scaleTime()
const yScale = scaleLinear()

const { prepareValueDomain, drawValueGrid, drawValueAxis, drawTimeAxis } = useAxes(
  axesContainer,
  xScale,
  yScale,
  plotWidth,
  plotHeight,
  yStepping,
  yTickFormatter
)

let m4Cache: M4Cache[] = []
function rebuildM4(): void {
  m4Cache = props.metrics.map((metric) => m4(metric.data_points, props.time_range, M4_BUCKETS))
}
watch(() => [props.metrics, props.time_range], rebuildM4, { immediate: true, deep: true })

// HiDPI: bitmap sized in physical pixels (cssSize * dpr), CSS size in logical pixels, the
// ctx transform keeps draw code in CSS-pixel coordinates regardless of DPR.
function draw(): void {
  const canvasEl = canvas.value
  if (!canvasEl) {
    return
  }
  const ctx = canvasEl.getContext('2d')
  if (!ctx) {
    return
  }

  const columnCount = Math.max(1, Math.floor(plotWidth.value))
  const visibleTimeRange: [number, number] = [props.time_range.start, props.time_range.end]
  const downsampledMetrics = m4Cache.map((cache) =>
    downsampleToColumns(cache, visibleTimeRange, columnCount)
  )

  // Inverse mirrors a metric below the baseline; stacking then resolves cumulative bands.
  const inverted = downsampledMetrics.map((buckets, i) =>
    props.metrics[i]!.render.inverse ? buckets.map((bucket) => invertBucket(bucket)) : buckets
  )
  const stacks = computeStackedSeries(props.metrics, inverted, consolidationFn.value)

  xScale
    .domain([new Date(props.time_range.start * 1000), new Date(props.time_range.end * 1000)])
    .range([0, plotWidth.value])

  // The tick algorithm measures available width in ex units. 1 ex ≈ half an em, and pt→px
  // is ×4/3, so pixels-per-ex ≈ font_size_pt · 2/3.
  const pixelsPerEx = (props.options.font_size_pt || 10) * (2 / 3)
  const widthEx = plotWidth.value / pixelsPerEx
  const xTicks = computeTimeAxis(
    props.time_range.start,
    props.time_range.end,
    widthEx,
    props.time_range.step
  )

  // Line metrics contribute their drawn extremes; stacked metrics their cumulative band
  // extents. Forced symmetric around zero when any metric is inverse.
  const domainBuckets = props.metrics.map((_, i) =>
    stacks[i]!.kind === 'area-stacked'
      ? stacks[i]!.bands.map((band) => ({
          gap: band.gap,
          minValue: Math.min(band.lower, band.upper),
          maxValue: Math.max(band.lower, band.upper)
        }))
      : inverted[i]!
  )
  const anyInverse = props.metrics.some((metric) => metric.render.inverse)
  const [rawYMin, rawYMax] = computeYDomain(domainBuckets, { symmetric: anyInverse })
  prepareValueDomain(rawYMin, rawYMax)
  yScale.range([plotHeight.value - CANVAS_Y_PADDING, CANVAS_Y_PADDING])

  // Setting width/height resets the 2d context state; setTransform must follow.
  const dpr = window.devicePixelRatio || 1
  canvasEl.width = Math.round(plotWidth.value * dpr)
  canvasEl.height = Math.round(plotHeight.value * dpr)
  canvasEl.style.width = `${plotWidth.value}px`
  canvasEl.style.height = `${plotHeight.value}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, plotWidth.value, plotHeight.value)

  drawData(ctx, props.metrics, inverted, stacks, xScale, yScale, {
    interpolator: props.curveInterpolator ?? 'linear'
  })

  drawValueGrid()
  drawTimeAxis(xTicks)
  drawValueAxis()
  if (axesContainer.value) {
    drawHorizontalLines(axesContainer.value, props.horizontal_lines, yScale, plotWidth.value)
  }
}

// Re-fires draw on every devicePixelRatio change (zoom, monitor switch): the media query
// matches the current DPR, and when it stops matching we redraw and re-register.
let dprMedia: MediaQueryList | null = null

function attachDPRWatcher() {
  const dpr = window.devicePixelRatio || 1
  dprMedia = window.matchMedia(`(resolution: ${dpr}dppx)`)
  dprMedia.addEventListener('change', onDPRChange, { once: true })
}

function onDPRChange() {
  draw()
  attachDPRWatcher()
}

onMounted(() => {
  draw()
  attachDPRWatcher()
})

onBeforeUnmount(() => {
  dprMedia?.removeEventListener('change', onDPRChange)
  dprMedia = null
})

watch(
  () => [
    props.metrics,
    props.time_range,
    props.size,
    props.consolidationFunction,
    props.curveInterpolator,
    props.horizontal_lines
  ],
  draw,
  { deep: true }
)
</script>

<template>
  <div
    class="graphing-time-series-graph"
    :style="{ width: `${figureWidth}px`, height: `${figureHeight}px` }"
  >
    <!-- The grid/axes SVG sits first so the data canvas draws on top of it (curves over
         grid lines, not behind them). -->
    <svg class="graphing-time-series-graph__svg" :width="figureWidth" :height="figureHeight">
      <g ref="axesContainer" :transform="`translate(${MARGIN.left},${MARGIN.top})`" />
    </svg>
    <canvas
      ref="canvas"
      class="graphing-time-series-graph__canvas"
      :style="{ left: `${MARGIN.left}px`, top: `${MARGIN.top}px` }"
    />
  </div>
</template>

<style scoped>
.graphing-time-series-graph {
  position: relative;

  .graphing-time-series-graph__canvas,
  .graphing-time-series-graph__svg {
    position: absolute;
    top: 0;
    left: 0;
  }

  .graphing-time-series-graph__svg {
    pointer-events: none;
  }
}

/* All selectors below reach D3-managed elements via :deep() (they never receive Vue's
   scoped data-v-* attribute) and include non-BEM D3 classes like .domain and .tick, so
   the pseudo-class and BEM rules are disabled for this block. */
/* stylelint-disable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */

/* y-axis (D3): hide the domain border path and redundant tick marks (grid lines serve
   that role). */
:deep(.graphing-time-series-graph__y-axis .domain),
:deep(.graphing-time-series-graph__y-axis .tick line) {
  display: none;
}

:deep(.graphing-time-series-graph__grid-y .tick line) {
  stroke: var(--ux-theme-6, #e0e0e0);
  stroke-dasharray: 2, 2;
}

:deep(.graphing-time-series-graph__grid-y .domain) {
  display: none;
}

/* x-axis: manually rendered from the ported time-axis ticks, not a D3 axis. */
:deep(.graphing-time-series-graph__x-grid line) {
  stroke: var(--ux-theme-6, #e0e0e0);
  shape-rendering: crispedges;
}

:deep(.graphing-time-series-graph__x-baseline line) {
  stroke: currentcolor;
  opacity: 0.35;
  shape-rendering: crispedges;
}

:deep(.graphing-time-series-graph__x-labels text) {
  fill: currentcolor;
  font-size: 11px;
  opacity: 0.8;
}

/* stylelint-enable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
</style>
