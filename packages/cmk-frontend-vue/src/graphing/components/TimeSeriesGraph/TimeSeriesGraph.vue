<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { scaleLinear, scaleTime } from 'd3-scale'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { ConsolidationFn } from '../consolidation'
import { CANVAS_MARGIN_LEFT, CANVAS_MARGIN_RIGHT, VALUE_LABEL_GUTTER } from '../constants'
import { measureAxisLabel } from './axes/labelWidth'
import { computeTimeAxis } from './axes/timeAxis'
import { computeYDomain } from './axes/valueAxis'
import { downsampleToColumns, m4 } from './decimation/decimate'
import type { M4Cache } from './decimation/types'
import OverlayLayer from './overlay/OverlayLayer.vue'
import PinHandle from './overlay/PinHandle.vue'
import { crosshairCentreX, pinLineCentreX } from './overlay/crosshair'
import { drawData } from './render'
import { invertBucket } from './render/bucket'
import { drawHorizontalLines } from './render/horizontalLines'
import { computeStackedSeries } from './render/stacked'
import type { PinPayload, TimeRange, TimeSeriesGraphProps, ZoomPayload } from './types'
import { useAxes } from './useAxes'
import { useHover } from './useHover'
import { usePanGesture } from './usePanGesture'
import { useZoomGesture } from './useZoomGesture'

const props = defineProps<TimeSeriesGraphProps>()

const emit = defineEmits<{
  pan: [{ timeRange: TimeRange }]
  zoom: [ZoomPayload]
  reset: []
  pinCreate: [PinPayload]
  pinAction: [PinPayload]
  'update:plotLeft': [number]
}>()

const consolidationFn = computed<ConsolidationFn>(() => props.consolidationFunction ?? 'avg')

const MARGIN = { top: 5, right: CANVAS_MARGIN_RIGHT, bottom: 24 } as const
const PIN_HANDLE_HEADROOM = 24
// Bucket count for the M4 cache built on receive (4000 is the default, consider changing
// if necessary).
const M4_BUCKETS = 4000

const canvas = ref<HTMLCanvasElement | null>(null)
const axesContainer = ref<SVGGElement | null>(null)

const measureLabel = (text: string): number => measureAxisLabel(text, axesContainer.value)

const marginLeft = ref(CANVAS_MARGIN_LEFT)

// size is the outer figure size; the plot (canvas) area is what remains after
// subtracting the axis/label margins.
const figureWidth = computed(() => props.size.width)
const figureHeight = computed(() => props.size.height)
const plotWidth = computed(() => figureWidth.value - marginLeft.value - MARGIN.right)
const plotTop = computed(() => MARGIN.top + (props.pinEnabled ? PIN_HANDLE_HEADROOM : 0))
const plotHeight = computed(() => figureHeight.value - plotTop.value - MARGIN.bottom)

const pinVisible = computed(
  () =>
    props.pinEnabled === true &&
    typeof props.pinTime === 'number' &&
    props.pinTime >= props.time_range.start &&
    props.pinTime <= props.time_range.end
)
const pinX = computed<number | null>(() => {
  if (!pinVisible.value || typeof props.pinTime !== 'number') {
    return null
  }
  const span = props.time_range.end - props.time_range.start
  if (span <= 0) {
    return null
  }
  return ((props.pinTime - props.time_range.start) / span) * plotWidth.value
})
const pinHandleX = computed<number | null>(() =>
  pinX.value === null ? null : pinLineCentreX(pinX.value)
)

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

const { prepareValueDomain, valueTickLabels, drawValueGrid, drawValueAxis, drawTimeAxis } = useAxes(
  axesContainer,
  xScale,
  yScale,
  plotWidth,
  plotHeight,
  yStepping,
  yTickFormatter
)

const {
  hoverState,
  recordDrawnGeometry,
  moveHoverTo,
  clearHover,
  cancelPendingHoverClear,
  clearHoverAfterDelay
} = useHover({
  metrics: () => props.metrics,
  consolidation: () => consolidationFn.value,
  plotWidth,
  plotHeight,
  xScale,
  yScale
})

const {
  selectionBand,
  plotCursor,
  onPlotMouseDown: startZoomSelection
} = useZoomGesture({
  zoomMode: () => props.zoomMode,
  timeRange: () => props.time_range,
  minTimeRange: () => props.minTimeRange,
  minValueRange: () => props.minValueRange,
  plotWidth,
  plotHeight,
  xScale,
  yScale,
  plotCoords,
  onZoom: (payload) => emit('zoom', payload)
})

const { panActive, panDx, panRulerTicks, panClipId, panCursor, panTickX, onPanMouseDown } =
  usePanGesture({
    panEnabled: () => props.panEnabled,
    timeRange: () => props.time_range,
    measureLabel,
    plotWidth,
    xScale,
    plotCoords,
    onStart: clearHover,
    onCommit: (timeRange) => emit('pan', { timeRange })
  })

// Rebuilt lazily inside draw() (rather than via its own watch(props.metrics, ...)) so it can
// never run stale relative to the time_range draw() is about to use: two independent
// watchers on overlapping-but-different prop sets give no ordering guarantee between them,
// and a m4Cache built against an old time_range but painted against a new one silently
// truncates the drawn data partway through the (now wider) axis.
let m4Cache: M4Cache[] = []
let m4CacheMetrics: TimeSeriesGraphProps['metrics'] | null = null
let m4CacheTimeRange: TimeRange | null = null
function ensureM4Cache(): void {
  if (m4CacheMetrics === props.metrics && m4CacheTimeRange === props.time_range) {
    return
  }
  m4CacheMetrics = props.metrics
  m4CacheTimeRange = props.time_range
  m4Cache = props.metrics.map((metric) => m4(metric.data_points, props.time_range, M4_BUCKETS))
}

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

  ensureM4Cache()

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
  recordDrawnGeometry(downsampledMetrics, stacks)

  xScale
    .domain([new Date(props.time_range.start * 1000), new Date(props.time_range.end * 1000)])
    .range([0, plotWidth.value])

  const xTicks = computeTimeAxis(
    props.time_range.start,
    props.time_range.end,
    plotWidth.value,
    props.time_range.step,
    measureLabel
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
  const [autoYMin, autoYMax] = computeYDomain(domainBuckets, { symmetric: anyInverse })
  const [rawYMin, rawYMax] = props.valueRange
    ? [props.valueRange.min, props.valueRange.max]
    : [autoYMin, autoYMax]
  prepareValueDomain(rawYMin, rawYMax)
  fitMarginToValueLabels()

  // Setting width/height resets the 2d context state; setTransform must follow.
  const dpr = window.devicePixelRatio || 1
  canvasEl.width = Math.round(plotWidth.value * dpr)
  canvasEl.height = Math.round(plotHeight.value * dpr)
  canvasEl.style.width = `${plotWidth.value}px`
  canvasEl.style.height = `${plotHeight.value}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, plotWidth.value, plotHeight.value)

  drawData(
    ctx,
    props.metrics,
    inverted,
    stacks,
    xScale,
    yScale,
    {
      interpolator: props.curveInterpolator ?? 'linear'
    },
    props.highlightedMetricName
  )

  drawValueGrid()
  drawTimeAxis(xTicks)
  drawValueAxis()
  if (axesContainer.value) {
    drawHorizontalLines(axesContainer.value, props.horizontal_lines, yScale, plotWidth.value)
  }
}

// The value axis is drawn into the left margin, so the margin has to hold the widest label
// the current domain produces. Writing it back grows plotWidth, which redraws once more with
// the labels the wider plot resolves to; that second pass settles.
function fitMarginToValueLabels(): void {
  const widestLabel = valueTickLabels().reduce(
    (widest, label) => Math.max(widest, measureLabel(label)),
    0
  )
  marginLeft.value = Math.max(CANVAS_MARGIN_LEFT, Math.ceil(widestLabel) + VALUE_LABEL_GUTTER)
}

function plotCoords(ev: MouseEvent): { x: number; y: number } | null {
  const canvasEl = canvas.value
  if (!canvasEl) {
    return null
  }
  const rect = canvasEl.getBoundingClientRect()
  return { x: ev.clientX - rect.left, y: ev.clientY - rect.top }
}

function onMouseMove(ev: MouseEvent): void {
  if (selectionBand.value) {
    return
  }
  const point = plotCoords(ev)
  moveHoverTo(point && { ...point, clientX: ev.clientX, clientY: ev.clientY })
}

function onPlotMouseDown(ev: MouseEvent): void {
  clearHover()
  startZoomSelection(ev)
}

function onPinAddClick(): void {
  const snapTime = hoverState.value?.snapTime
  if (typeof snapTime === 'number') {
    emit('pinCreate', { time: snapTime })
  }
}
function onPinActionClick(): void {
  if (typeof props.pinTime === 'number') {
    emit('pinAction', { time: props.pinTime })
  }
}

const { _t } = usei18n()
const resetLabel = _t('Reset zoom')
const fallbackPlotLabel = _t('Time series graph')
// Accessible name for the plot canvas
const plotAriaLabel = computed<string>(() => {
  if (props.options.header.title) {
    return props.options.header.title
  }
  const metricTitles = props.metrics
    .map((metric) => metric.metadata.title)
    .filter((title) => title !== '')
  return metricTitles.length > 0 ? metricTitles.join(', ') : fallbackPlotLabel
})
function onResetClick(): void {
  emit('reset')
}
function onPlotKeydown(ev: KeyboardEvent): void {
  if (ev.key !== 'Home') {
    return
  }
  ev.preventDefault()
  emit('reset')
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
    props.valueRange,
    props.size,
    props.consolidationFunction,
    props.curveInterpolator,
    props.horizontal_lines,
    props.highlightedMetricName,
    plotWidth.value
  ],
  draw,
  { deep: true }
)

watch(marginLeft, (left) => emit('update:plotLeft', left), { immediate: true })
</script>

<template>
  <div
    class="graphing-time-series-graph"
    :class="{ 'graphing-time-series-graph--panning-x': panActive }"
    :style="{ width: `${figureWidth}px`, height: `${figureHeight}px` }"
  >
    <!-- The grid/axes SVG sits first so the data canvas draws on top of it (curves over
         grid lines, not behind them). It is visual scaffolding; the plot canvas carries
         the accessible name for the graph. -->
    <svg
      class="graphing-time-series-graph__svg"
      :width="figureWidth"
      :height="figureHeight"
      aria-hidden="true"
    >
      <defs>
        <!-- Trims the sliding ruler to the plot's bottom strip so off-window labels
             don't spill over the y-axis numbers / margin. -->
        <clipPath :id="panClipId">
          <rect
            :x="marginLeft"
            :y="plotTop + plotHeight"
            :width="plotWidth"
            :height="MARGIN.bottom"
          />
        </clipPath>
      </defs>
      <rect
        class="graphing-time-series-graph__plot-background"
        :x="marginLeft"
        :y="plotTop"
        :width="plotWidth"
        :height="plotHeight"
      />
      <g ref="axesContainer" :transform="`translate(${marginLeft},${plotTop})`" />
      <!-- Ruler-scrub overlay (pan preview): a shaded band plus ticks/labels that slide
           with the cursor, clipped to the plot width. Only mounted while dragging. -->
      <g v-if="panActive" :clip-path="`url(#${panClipId})`">
        <rect
          class="graphing-time-series-graph__pan-band"
          :x="marginLeft"
          :y="plotTop + plotHeight + 1"
          :width="plotWidth"
          :height="MARGIN.bottom - 1"
        />
        <g :transform="`translate(${marginLeft + panDx},${plotTop})`">
          <template v-for="(tick, index) in panRulerTicks" :key="index">
            <line
              v-if="tick.lineWidth > 0"
              class="graphing-time-series-graph__pan-tick"
              :x1="panTickX(tick)"
              :x2="panTickX(tick)"
              :y1="plotHeight"
              :y2="plotHeight + 5"
            />
            <text
              v-if="tick.text !== null"
              class="graphing-time-series-graph__pan-label"
              :x="panTickX(tick)"
              :y="plotHeight + 14"
              text-anchor="middle"
            >
              {{ tick.text }}
            </text>
          </template>
        </g>
      </g>
    </svg>
    <canvas
      ref="canvas"
      class="graphing-time-series-graph__canvas"
      tabindex="0"
      role="img"
      :aria-label="plotAriaLabel"
      :style="{ left: `${marginLeft}px`, top: `${plotTop}px`, cursor: plotCursor }"
      @mousemove="onMouseMove"
      @mouseleave="clearHoverAfterDelay"
      @mousedown="onPlotMouseDown"
      @keydown="onPlotKeydown"
      @contextmenu.prevent
    />
    <OverlayLayer
      :hover-state="hoverState"
      :plot-width="plotWidth"
      :plot-height="plotHeight"
      :pin-x="pinX"
      :style="{ left: `${marginLeft}px`, top: `${plotTop}px` }"
    />
    <div
      v-if="selectionBand"
      class="graphing-time-series-graph__zoom-band"
      :style="{
        left: `${marginLeft + selectionBand.x}px`,
        top: `${plotTop + selectionBand.y}px`,
        width: `${selectionBand.width}px`,
        height: `${selectionBand.height}px`
      }"
    />
    <!-- Transparent grab strip over the x-axis labels; arms the pan drag. -->
    <div
      v-if="panEnabled"
      class="graphing-time-series-graph__pan-zone"
      :style="{
        left: `${marginLeft}px`,
        top: `${plotTop + plotHeight}px`,
        width: `${plotWidth}px`,
        height: `${MARGIN.bottom}px`,
        cursor: panCursor
      }"
      @mousedown="onPanMouseDown"
    />
    <CmkButton
      v-if="inspecting"
      variant="secondary"
      size="small"
      class="graphing-time-series-graph__reset"
      :style="{ top: `${plotTop + 6}px`, right: `${MARGIN.right + 6}px` }"
      :title="resetLabel"
      :aria-label="resetLabel"
      @click="onResetClick"
    >
      <CmkIcon name="reload" size="small" />
      <span>{{ resetLabel }}</span>
    </CmkButton>
    <PinHandle
      v-if="pinHandleX !== null"
      variant="remove"
      :style="{ left: `${marginLeft + pinHandleX}px`, top: `${plotTop}px` }"
      @action="onPinActionClick"
    />
    <PinHandle
      v-if="pinEnabled && hoverState"
      variant="add"
      :style="{
        left: `${marginLeft + crosshairCentreX(hoverState.snapX)}px`,
        top: `${plotTop}px`
      }"
      @action="onPinAddClick"
      @mouseenter="cancelPendingHoverClear"
      @mouseleave="clearHoverAfterDelay"
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

  .graphing-time-series-graph__plot-background {
    fill: var(--ux-theme-1);
  }

  .graphing-time-series-graph__zoom-band {
    position: absolute;
    z-index: 1;
    pointer-events: none;
    background: color-mix(in srgb, var(--color-light-blue-50) 15%, transparent);
    border: var(--border-width-1) solid
      color-mix(in srgb, var(--color-light-blue-50) 60%, transparent);
  }

  .graphing-time-series-graph__pan-zone {
    position: absolute;
    z-index: 2;
    background: transparent;
  }

  .graphing-time-series-graph__reset {
    position: absolute;
    z-index: 2;
    gap: var(--dimension-3);
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

/* Match the x-axis label size; without this the D3 axis text renders at the inherited page
   font size rather than the token the x-axis uses. */
:deep(.graphing-time-series-graph__y-axis text) {
  font-size: var(--font-size-small);
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
  font-size: var(--font-size-small);
  opacity: 0.8;
}

.graphing-time-series-graph--panning-x :deep(.graphing-time-series-graph__x-labels) {
  opacity: 0;
}

:deep(.graphing-time-series-graph__pan-band) {
  fill: rgb(0 0 0 / 4%);
  shape-rendering: crispedges;
}

:deep(.graphing-time-series-graph__pan-tick) {
  stroke: currentcolor;
  opacity: 0.35;
  shape-rendering: crispedges;
}

:deep(.graphing-time-series-graph__pan-label) {
  fill: currentcolor;
  font-size: var(--font-size-small);
  opacity: 0.8;
}

/* stylelint-enable selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
</style>
