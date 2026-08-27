<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { NotationFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { userSpecificUnit } from 'cmk-ui-library/lib/unit-format/unitFormatter'
import { scaleLinear, scaleTime } from 'd3-scale'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from '../consolidation'
import {
  CANVAS_MARGIN_LEFT,
  PLOT_INSET_X,
  PLOT_INSET_Y,
  VALUE_AXIS_ROOM_MIN,
  VALUE_LABEL_TICK_OFFSET
} from '../constants'
import { axisLabelFontSize, measureAxisLabel } from './axes/labelWidth'
import { computeTimeAxis } from './axes/timeAxis'
import OverlayLayer from './overlay/OverlayLayer.vue'
import PinHandle from './overlay/PinHandle.vue'
import { crosshairCentreX, pinLineCentreX } from './overlay/crosshair'
import { drawData } from './render'
import {
  composeSeries,
  composedValueDomain,
  createM4CacheStore,
  withoutOffPlotNeighbours
} from './render/composeSeries'
import { drawHorizontalLines } from './render/horizontalLines'
import type { PinPayload, TimeRange, TimeSeriesGraphProps, ZoomPayload } from './types'
import { useAxes } from './useAxes'
import { useHover } from './useHover'
import { usePanGesture } from './usePanGesture'
import { useZoomGesture } from './useZoomGesture'

const props = withDefaults(defineProps<TimeSeriesGraphProps>(), {
  showTimeAxis: true,
  showValueAxis: true
})

const emit = defineEmits<{
  pan: [{ timeRange: TimeRange }]
  zoom: [ZoomPayload]
  reset: []
  pinCreate: [PinPayload]
  pinAction: [PinPayload]
  'update:plotLeft': [number]
}>()

const consolidationFn = computed<ConsolidationFn>(
  () => props.consolidationFunction ?? DEFAULT_CONSOLIDATION_FN
)

const MAX_ZOOM_HINT_DURATION_MS = 1200
const MAX_ZOOM_HINT_CURSOR_OFFSET = 12
const maxZoomHintAt = ref<{ x: number; y: number } | null>(null)
let maxZoomHintTimer: ReturnType<typeof setTimeout> | null = null

function showMaxZoomHint(point: { x: number; y: number }): void {
  maxZoomHintAt.value = point
  if (maxZoomHintTimer !== null) {
    clearTimeout(maxZoomHintTimer)
  }
  maxZoomHintTimer = setTimeout(() => {
    maxZoomHintAt.value = null
    maxZoomHintTimer = null
  }, MAX_ZOOM_HINT_DURATION_MS)
}

const X_AXIS_BAND_HEIGHT = 20
// The strip's top edge doubles as the plot's baseline rule, so anything laid over the strip
// starts below it rather than covering it.
const X_AXIS_TOP_RULE_HEIGHT = 1
const PAN_STEP_SIZE = X_AXIS_BAND_HEIGHT - X_AXIS_TOP_RULE_HEIGHT
// Bucket count for the M4 cache built on receive (4000 is the default, consider changing
// if necessary).
const M4_BUCKETS = 4000

const canvas = ref<HTMLCanvasElement | null>(null)
const axesContainer = ref<SVGGElement | null>(null)

const measureLabel = (text: string): number => measureAxisLabel(text, axesContainer.value)

const panAffordancesVisible = computed(() => props.panEnabled && props.showTimeAxis)

const marginLeft = ref(CANVAS_MARGIN_LEFT)
const halfAValueLabel = computed(() => Math.ceil(axisLabelFontSize(axesContainer.value) / 2))
const marginBottom = computed(() => {
  if (props.showTimeAxis) {
    return PLOT_INSET_Y + X_AXIS_BAND_HEIGHT
  }
  // The value axis' lowest label overhangs the plot's bottom edge by half a line. With no time
  // axis band beneath it, the frame padding is what has to clear it.
  const lowestValueLabelOverhang = props.showValueAxis ? halfAValueLabel.value : 0
  return Math.max(PLOT_INSET_Y, lowestValueLabelOverhang)
})

// size is the outer figure size; the plot (canvas) area is what remains after
// subtracting the axis/label margins.
const figureWidth = computed(() => props.size.width)
const figureHeight = computed(() => props.size.height)
const plotWidth = computed(() => figureWidth.value - marginLeft.value - PLOT_INSET_X)
const plotTop = PLOT_INSET_Y
const plotHeight = computed(() => figureHeight.value - plotTop - marginBottom.value)

const pinVisible = computed(
  () =>
    props.pinEnabled === true &&
    typeof props.pinTime === 'number' &&
    props.pinTime >= props.view_time_range.start &&
    props.pinTime <= props.view_time_range.end
)
const pinX = computed<number | null>(() => {
  if (!pinVisible.value || typeof props.pinTime !== 'number') {
    return null
  }
  const span = props.view_time_range.end - props.view_time_range.start
  if (span <= 0) {
    return null
  }
  return ((props.pinTime - props.view_time_range.start) / span) * plotWidth.value
})
const pinHandleX = computed<number | null>(() =>
  pinX.value === null ? null : pinLineCentreX(pinX.value)
)

const maxZoomHintStyle = computed(() => {
  const point = maxZoomHintAt.value
  if (point === null) {
    return {}
  }
  return {
    top: `${plotTop + point.y + MAX_ZOOM_HINT_CURSOR_OFFSET}px`,
    left: `${marginLeft.value + point.x}px`
  }
})

// Laid out to the cursor's left in the right half of the plot, so a wide hint stays inside.
const maxZoomHintSide = computed(() =>
  maxZoomHintAt.value !== null && maxZoomHintAt.value.x > plotWidth.value / 2 ? 'left' : 'right'
)

// 'iec' notation is 1024-based so its ticks step in binary; every other notation is decimal.
const yStepping = computed((): 'binary' | 'decimal' =>
  props.options.y_axis?.unit.notation === 'iec' ? 'binary' : 'decimal'
)
// The axis unit places the labels, not just their text: renderYLabels steps in the unit's own
// atoms, so an IEC axis lands on 2 MiB rather than on a decimally round 2 * 10^6 bytes.
const yFormatter = computed((): NotationFormatter | null => {
  const unit = props.options.y_axis?.unit
  return unit ? userSpecificUnit(unit, 'celsius').formatter : null
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
  yFormatter
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

// Stacked on the pinned sample, the add marker would swallow the remove marker's click.
const hoverAtPin = computed(
  () =>
    pinX.value !== null &&
    hoverState.value !== null &&
    Math.round(hoverState.value.snapX) === Math.round(pinX.value)
)

const {
  selectionBand,
  plotCursor,
  onPlotMouseDown: startZoomSelection
} = useZoomGesture({
  zoomMode: () => props.zoomMode,
  timeRange: () => props.view_time_range,
  minTimeRange: () => props.minTimeRange,
  minValueRange: () => props.minValueRange,
  valueRange: () => props.valueRange,
  atTimeFloor: () => props.atMinTimeZoom === true,
  plotWidth,
  plotHeight,
  xScale,
  yScale,
  plotCoords,
  onZoom: (payload) => emit('zoom', payload),
  onZoomRefused: showMaxZoomHint,
  onPlotClick: setPinAtCursor
})

const {
  panActive,
  panDx,
  panRulerTicks,
  panClipId,
  panCursor,
  panTickX,
  onPanMouseDown,
  panBySteps
} = usePanGesture({
  panEnabled: () => panAffordancesVisible.value,
  timeRange: () => props.view_time_range,
  measureLabel,
  plotWidth,
  xScale,
  plotCoords,
  onStart: clearHover,
  onCommit: (timeRange) => emit('pan', { timeRange })
})

const m4CacheStore = createM4CacheStore(M4_BUCKETS)

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

  const composed = composeSeries({
    metrics: props.metrics,
    cache: m4CacheStore.ensure(props.metrics, props.data_time_range ?? props.view_time_range),
    visibleTimeRange: [props.view_time_range.start, props.view_time_range.end],
    columnCount: Math.max(1, Math.floor(plotWidth.value)),
    consolidation: consolidationFn.value
  })
  const { paddedBuckets: inverted, stacks } = composed

  recordDrawnGeometry(
    composed.bucketsOnPlot,
    stacks.map((series) => ({ ...series, bands: withoutOffPlotNeighbours(series.bands) }))
  )

  xScale
    .domain([
      new Date(props.view_time_range.start * 1000),
      new Date(props.view_time_range.end * 1000)
    ])
    .range([0, plotWidth.value])

  const xTicks = computeTimeAxis(
    props.view_time_range.start,
    props.view_time_range.end,
    plotWidth.value,
    props.view_time_range.step,
    measureLabel
  )

  const [autoYMin, autoYMax] = composedValueDomain(props.metrics, composed)
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
  drawTimeAxis(xTicks, { showLabels: props.showTimeAxis })
  drawValueAxis({ showLabels: props.showValueAxis })
  if (axesContainer.value) {
    drawHorizontalLines(axesContainer.value, props.horizontal_lines, yScale, plotWidth.value)
  }
}

// Guard against cycling through
//    watch(plotWidth) -> draw() -> fitMarginToValueLabels() -> set marginLeft -> watch(plotWidth)
// for adjacent plot widths with different label widths. In that case we keep the larger margin and
// refuse the lower one (refusedLowMargin).
let lastMargin = CANVAS_MARGIN_LEFT
let refusedLowMargin: number | null = null

// The value axis is drawn into the left margin, so the margin has to hold the widest label
// the current domain produces on top of the frame padding. Writing it back grows plotWidth,
// which redraws once more with the labels the wider plot resolves to; that second pass settles.
function fitMarginToValueLabels(): void {
  if (!props.showValueAxis) {
    // No axis room to reserve, but the frame padding stands so the plot keeps the same
    // breathing room on both sides.
    marginLeft.value = PLOT_INSET_X
    lastMargin = PLOT_INSET_X
    refusedLowMargin = null
    return
  }

  const widestLabel = valueTickLabels().reduce(
    (widest, label) => Math.max(widest, measureLabel(label)),
    0
  )
  const axisRoom = Math.max(
    props.minValueAxisWidth ?? VALUE_AXIS_ROOM_MIN,
    Math.ceil(widestLabel) + VALUE_LABEL_TICK_OFFSET
  )
  const next = PLOT_INSET_X + axisRoom

  // Holding the high end of a detected flip: ignore the low value that keeps recurring.
  if (next === refusedLowMargin) {
    return
  }
  refusedLowMargin = null

  if (next === marginLeft.value) {
    lastMargin = next
    return
  }

  if (next === lastMargin) {
    // Detected sequence A -> B -> A (last -> current -> next === last)
    // Hold the larger value so labels never clip; refuse the smaller one in the next iteration to
    // break the cycle
    refusedLowMargin = Math.min(next, marginLeft.value)
    marginLeft.value = Math.max(next, marginLeft.value)
    lastMargin = marginLeft.value
    return
  }

  lastMargin = marginLeft.value
  marginLeft.value = next
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
// The press cleared the hover to keep the crosshair out of a zoom drag, so it is recomputed
// here for the time to pin.
function setPinAtCursor(ev: MouseEvent): void {
  if (props.pinEnabled !== true) {
    return
  }
  onMouseMove(ev)
  onPinAddClick()
}
function onPinActionClick(): void {
  if (typeof props.pinTime === 'number') {
    emit('pinAction', { time: props.pinTime })
  }
}

const { _t } = usei18n()
const resetLabel = _t('Reset zoom')
const maxZoomLabel = _t('Maximum zoom reached')
const panHovered = ref(false)
const PAN_STEPS = [
  { direction: -1, side: 'back', label: _t('Step back in time') },
  { direction: 1, side: 'forward', label: _t('Step forward in time') }
] as const
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
  if (maxZoomHintTimer !== null) {
    clearTimeout(maxZoomHintTimer)
    maxZoomHintTimer = null
  }
})

watch(
  () => [
    props.metrics,
    props.view_time_range,
    props.valueRange,
    props.size,
    props.consolidationFunction,
    props.curveInterpolator,
    props.horizontal_lines,
    props.highlightedMetricName,
    plotWidth.value,
    props.showTimeAxis,
    props.showValueAxis,
    props.minValueAxisWidth
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
            :height="marginBottom"
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
      <rect
        v-if="showTimeAxis"
        class="graphing-time-series-graph__axis-band"
        :x="marginLeft"
        :y="plotTop + plotHeight"
        :width="plotWidth"
        :height="X_AXIS_BAND_HEIGHT"
      />
      <rect
        v-if="panAffordancesVisible && (panHovered || panActive)"
        class="graphing-time-series-graph__axis-highlight"
        :x="marginLeft"
        :y="plotTop + plotHeight"
        :width="plotWidth"
        :height="X_AXIS_BAND_HEIGHT"
      />
      <g ref="axesContainer" :transform="`translate(${marginLeft},${plotTop})`" />
      <!-- Ruler-scrub overlay (pan preview): ticks/labels that slide with the cursor, clipped
           to the plot width. Only mounted while dragging. -->
      <g v-if="panActive" :clip-path="`url(#${panClipId})`">
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
      v-if="panAffordancesVisible"
      class="graphing-time-series-graph__pan-zone"
      :style="{
        left: `${marginLeft}px`,
        top: `${plotTop + plotHeight}px`,
        width: `${plotWidth}px`,
        height: `${marginBottom}px`,
        cursor: panCursor
      }"
      @mousedown="onPanMouseDown"
      @mouseenter="panHovered = true"
      @mouseleave="panHovered = false"
    />
    <template v-if="panAffordancesVisible">
      <CmkButton
        v-for="step in PAN_STEPS"
        :key="step.direction"
        variant="secondary"
        size="iconOnly"
        class="graphing-time-series-graph__pan-step"
        :class="`graphing-time-series-graph__pan-step--${step.side}`"
        :style="{
          left: `${step.direction === -1 ? marginLeft : marginLeft + plotWidth - PAN_STEP_SIZE}px`,
          top: `${plotTop + plotHeight + X_AXIS_TOP_RULE_HEIGHT}px`,
          width: `${PAN_STEP_SIZE}px`,
          height: `${PAN_STEP_SIZE}px`
        }"
        :title="step.label"
        :aria-label="step.label"
        @click="panBySteps(step.direction)"
      >
        <ArrowDown class="graphing-time-series-graph__pan-caret" aria-hidden="true" />
      </CmkButton>
    </template>
    <CmkButton
      v-if="inspecting"
      variant="secondary"
      size="small"
      class="graphing-time-series-graph__reset"
      :style="{ top: `${plotTop + 6}px`, right: `${PLOT_INSET_X + 6}px` }"
      :title="resetLabel"
      :aria-label="resetLabel"
      @click="onResetClick"
    >
      <CmkIcon
        name="arrows-swap"
        class="graphing-time-series-graph__reset-icon"
        aria-hidden="true"
      />
      <span>{{ resetLabel }}</span>
    </CmkButton>
    <!-- A zero-size anchor at the cursor; the tooltip lays the hint out beside it. -->
    <div
      v-if="maxZoomHintAt"
      class="graphing-time-series-graph__max-zoom-hint"
      :style="maxZoomHintStyle"
    >
      <CmkTooltipProvider>
        <CmkTooltip :open="true">
          <CmkTooltipTrigger as="span" />
          <CmkTooltipContent
            :side="maxZoomHintSide"
            :side-offset="MAX_ZOOM_HINT_CURSOR_OFFSET"
            align="start"
            :avoid-collisions="false"
          >
            <div class="graphing-time-series-graph__max-zoom-hint-body" role="status">
              {{ maxZoomLabel }}
            </div>
          </CmkTooltipContent>
        </CmkTooltip>
      </CmkTooltipProvider>
    </div>
    <PinHandle
      v-if="pinHandleX !== null"
      variant="remove"
      :style="{ left: `${marginLeft + pinHandleX}px`, top: `${plotTop}px` }"
      @action="onPinActionClick"
    />
    <PinHandle
      v-if="pinEnabled && hoverState && !hoverAtPin"
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

  .graphing-time-series-graph__axis-band {
    fill: var(--ux-theme-5);
  }

  .graphing-time-series-graph__axis-highlight {
    fill: var(--graphing-interactive-wash);
  }

  .graphing-time-series-graph__zoom-band {
    position: absolute;
    z-index: 1;
    pointer-events: none;
    background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  }

  .graphing-time-series-graph__pan-zone {
    position: absolute;
    z-index: 2;
    background: transparent;
  }

  .graphing-time-series-graph__reset {
    position: absolute;
    z-index: 2;
    height: var(--dimension-8);
    gap: var(--dimension-3);
  }

  .graphing-time-series-graph__reset-icon {
    flex-shrink: 0;
    width: var(--dimension-6);
    height: var(--dimension-6);
  }

  /* Above the pan zone, which would otherwise swallow the clicks. */
  .graphing-time-series-graph__pan-step {
    position: absolute;
    z-index: 3;
    background-color: var(--ux-theme-0);
    border-color: var(--toggle-button-group-border-color);

    &:hover {
      background-image: linear-gradient(
        var(--graphing-interactive-wash),
        var(--graphing-interactive-wash)
      );
    }

    /* Fades out the tick labels running up to the button, so none collides with it. */
    &::after {
      content: '';
      position: absolute;
      top: 0;
      bottom: 0;
      width: var(--dimension-8);
      pointer-events: none;
    }
  }

  .graphing-time-series-graph__pan-caret {
    flex-shrink: 0;
    width: var(--dimension-4);
  }

  /* Offset past the border: a bare `100%` resolves to the padding box and hides it. */
  .graphing-time-series-graph__pan-step--back {
    .graphing-time-series-graph__pan-caret {
      transform: rotate(90deg);
    }

    &::after {
      left: calc(100% + var(--border-width-1));
      background: linear-gradient(to right, var(--ux-theme-5), transparent);
    }
  }

  .graphing-time-series-graph__pan-step--forward {
    .graphing-time-series-graph__pan-caret {
      transform: rotate(-90deg);
    }

    &::after {
      right: calc(100% + var(--border-width-1));
      background: linear-gradient(to left, var(--ux-theme-5), transparent);
    }
  }

  .graphing-time-series-graph__max-zoom-hint {
    position: absolute;
    z-index: 3;
    pointer-events: none;
  }

  .graphing-time-series-graph__max-zoom-hint-body {
    box-sizing: border-box;
    max-width: 260px;
    padding: var(--dimension-4);
    background: var(--default-tooltip-background-color);
    border: var(--border-width-1) solid var(--default-tooltip-text-color);
    border-radius: var(--border-radius);
    font-size: var(--font-size-normal);
    line-height: normal;
    color: var(--default-tooltip-text-color);
  }
}

body[data-theme='facelift'] {
  .graphing-time-series-graph {
    --graphing-interactive-wash: var(--color-conference-grey-10);
  }
}

body[data-theme='modern-dark'] {
  .graphing-time-series-graph {
    --graphing-interactive-wash: var(--color-white-10);
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
