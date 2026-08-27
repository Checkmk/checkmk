<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import useId from 'cmk-ui-library/lib/useId'
import { area } from 'd3-shape'
import { computed, onBeforeUnmount, ref } from 'vue'

import type { TimeInterval, TimeRangeCommitKind } from '../../types'
import type { Metric, RequestedTimeRange, TimeRange } from '../TimeSeriesGraph'
import { timestampAt } from '../TimeSeriesGraph/axes/timeAxis'
import {
  type BrushMode,
  clampMove,
  hitTestMode,
  pxToTime,
  recenter,
  resizeHandleRects,
  resizeLeft,
  resizeRight,
  timeToPx
} from './geometry'
import { computeSparklineBands, formatOverviewExtent, formatWindowPreview } from './utils'

const props = defineProps<{
  metrics: Metric[] // coarse overview series
  domain: TimeInterval // strip extent
  dataDomain: TimeRange
  window: { start: number; end: number }
  minSpan: number | null
  width: number // figure width (px)
  plotLeft: number // track left inset (= renderer MARGIN.left)
  plotWidth: number // track width (= plot width)
}>()

const emit = defineEmits<{
  'update:requestedTimeRange': [RequestedTimeRange, TimeRangeCommitKind]
}>()

const DRAG_THRESHOLD_PX = 4

const STRIP_TOP = 9
const STRIP_H = 32
const STRIP_BOTTOM = STRIP_TOP + STRIP_H
const BAR_Y = 45
const BAR_H = 8
const TRACK_TOP = STRIP_TOP
const TRACK_H = BAR_Y + BAR_H - TRACK_TOP
const TRACK_BOTTOM = TRACK_TOP + TRACK_H

const EDGE_TOP = TRACK_TOP
const EDGE_BOTTOM = BAR_Y + BAR_H
const HANDLE_W = 8
const HANDLE_H = 16
const HANDLE_TOP = (STRIP_TOP + STRIP_BOTTOM) / 2 - HANDLE_H / 2
const HANDLE_GRIP_DX = [-2, 0, 2]
const HANDLE_GRIP_Y1 = HANDLE_TOP + 4
const HANDLE_GRIP_Y2 = HANDLE_TOP + HANDLE_H - 4

const LABEL_GAP = 6
const LABEL_Y = EDGE_BOTTOM + LABEL_GAP + 8 // baseline (+8 ≈ the 11px label's cap height)
const HEIGHT = LABEL_Y + 4 // room below the baseline for descenders

const toPx = (time: number) =>
  timeToPx(time, props.domain.start, props.domain.end, props.plotLeft, props.plotWidth)
const toTime = (px: number) =>
  pxToTime(px, props.domain.start, props.domain.end, props.plotLeft, props.plotWidth)

const sparklinePaths = computed<{ d: string; color: string }[]>(() => {
  const { bands, sampleCount, yMin, yMax } = computeSparklineBands(props.metrics)
  if (sampleCount === 0) {
    return []
  }
  const sampleTimes = Array.from({ length: sampleCount }, (_, i) =>
    timestampAt(props.dataDomain, i)
  )
  const withinStrip = (i: number) =>
    sampleTimes[i]! >= props.domain.start && sampleTimes[i]! <= props.domain.end
  const span = yMax - yMin || 1
  // Maps the value domain into the strip (STRIP_TOP..STRIP_BOTTOM); the move-bar sits below it.
  const yPx = (value: number) => STRIP_BOTTOM - ((value - yMin) / span) * STRIP_H

  return bands.map(({ lower, upper, color }) => {
    const gen = area<number>()
      .defined((_, i) => withinStrip(i))
      .x((_, i) => toPx(sampleTimes[i]!))
      .y0((_, i) => yPx(lower[i]!))
      .y1((_, i) => yPx(upper[i]!))
    return { d: gen(lower) ?? '', color }
  })
})

const svgRef = ref<SVGSVGElement | null>(null)
const preview = ref<{ start: number; end: number } | null>(null)
const dragging = ref(false)
const winRange = computed(() => preview.value ?? props.window)
const winLeftPx = computed(() => toPx(winRange.value.start))
const winRightPx = computed(() => toPx(winRange.value.end))

const resizeHandleBounds = computed(() =>
  resizeHandleRects(winLeftPx.value, winRightPx.value, HANDLE_W)
)

const edgeHandles = computed(() =>
  [
    { edgeX: winLeftPx.value, rectX: resizeHandleBounds.value.leftX },
    { edgeX: winRightPx.value, rectX: resizeHandleBounds.value.rightX }
  ].map(({ edgeX, rectX }) => ({
    edgeX,
    rectX,
    grips: HANDLE_GRIP_DX.map((dx) => rectX + HANDLE_W / 2 + dx)
  }))
)

const rangeLabel = computed(() => formatOverviewExtent(props.domain))

const windowClipId = `brush-window-clip-${useId()}`

const windowPreview = computed(() => formatWindowPreview(winRange.value))
const windowLabelX = computed(() => (winLeftPx.value + winRightPx.value) / 2)

let mode: BrushMode = 'move'
let grabOffset = 0 // seconds between cursor and window.start (move)

const localX = (ev: MouseEvent) => ev.clientX - (svgRef.value?.getBoundingClientRect().left ?? 0)
const localY = (ev: MouseEvent) => ev.clientY - (svgRef.value?.getBoundingClientRect().top ?? 0)

// The svg spans the whole figure; only the track and its handles are interactive.
function onTrack(x: number, y: number): boolean {
  return (
    x >= props.plotLeft &&
    x <= props.plotLeft + props.plotWidth &&
    y >= TRACK_TOP &&
    y <= TRACK_BOTTOM
  )
}

function onResizeHandle(x: number, y: number): boolean {
  if (y < HANDLE_TOP || y > HANDLE_TOP + HANDLE_H) {
    return false
  }
  const { leftX, rightX, width } = resizeHandleBounds.value
  return (x >= leftX && x <= leftX + width) || (x >= rightX && x <= rightX + width)
}

function onMouseDown(ev: MouseEvent): void {
  const x = localX(ev)
  const y = localY(ev)
  if (ev.button !== 0 || !(onTrack(x, y) || onResizeHandle(x, y))) {
    return
  }
  ev.preventDefault()
  const span = props.window.end - props.window.start
  mode = hitTestMode(x, toPx(props.window.start), toPx(props.window.end), resizeHandleBounds.value)
  if (mode === 'recenter') {
    const [s, e] = recenter(toTime(x), span, props.domain.start, props.domain.end)
    preview.value = { start: s, end: e }
    grabOffset = toTime(x) - s
    mode = 'move'
  } else if (mode === 'move') {
    grabOffset = toTime(x) - props.window.start
  }
  dragging.value = true
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(ev: MouseEvent): void {
  const time = toTime(localX(ev))
  const span = props.window.end - props.window.start
  const floor = props.minSpan ?? 60
  if (mode === 'move') {
    const [s, e] = clampMove(
      time - grabOffset,
      time - grabOffset + span,
      props.domain.start,
      props.domain.end
    )
    preview.value = { start: s, end: e }
  } else if (mode === 'resize-l') {
    preview.value = {
      start: resizeLeft(time, props.window.end, props.domain.start, floor),
      end: props.window.end
    }
  } else if (mode === 'resize-r') {
    preview.value = {
      start: props.window.start,
      end: resizeRight(time, props.window.start, props.domain.end, floor)
    }
  }
}

function onUp(): void {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
  dragging.value = false
  const next = preview.value
  preview.value = null
  if (!next) {
    return
  }
  if (
    Math.abs(toPx(next.start) - toPx(props.window.start)) < DRAG_THRESHOLD_PX &&
    Math.abs(toPx(next.end) - toPx(props.window.end)) < DRAG_THRESHOLD_PX
  ) {
    return
  }
  emit(
    'update:requestedTimeRange',
    { start: Math.round(next.start), end: Math.round(next.end) },
    mode === 'move' ? 'translated_timerange' : 'changed_timerange_span'
  )
}

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
})
</script>

<template>
  <div
    class="graphing-graph-brush"
    :class="{ 'graphing-graph-brush--dragging': dragging }"
    :style="{ width: `${width}px`, height: `${HEIGHT}px` }"
  >
    <svg
      ref="svgRef"
      class="graphing-graph-brush__track-svg"
      :width="width"
      :height="HEIGHT"
      @mousedown="onMouseDown"
    >
      <!-- Outer track encloses the waveform strip and the move-bar below it. -->
      <rect
        class="graphing-graph-brush__track"
        :x="plotLeft"
        :y="TRACK_TOP"
        :width="plotWidth"
        :height="TRACK_H"
      />
      <defs>
        <clipPath :id="windowClipId">
          <rect
            :x="winLeftPx"
            :y="STRIP_TOP"
            :width="Math.max(0, winRightPx - winLeftPx)"
            :height="STRIP_H"
          />
        </clipPath>
      </defs>
      <!-- Coarse cumulative-area sparkline (the overview waveform), painted twice: dimmed
         across the strip, then at full strength clipped to the selection window. -->
      <g class="graphing-graph-brush__waveform--dimmed">
        <path
          v-for="(p, i) in sparklinePaths"
          :key="`area-dim-${i}`"
          class="graphing-graph-brush__area"
          :d="p.d"
          :fill="p.color"
        />
      </g>
      <g :clip-path="`url(#${windowClipId})`">
        <path
          v-for="(p, i) in sparklinePaths"
          :key="`area-${i}`"
          class="graphing-graph-brush__area"
          :d="p.d"
          :fill="p.color"
        />
      </g>
      <!-- Invisible, but it is what makes a click anywhere on the strip recentre the window. -->
      <rect
        class="graphing-graph-brush__hit-area"
        :x="plotLeft"
        :y="STRIP_TOP"
        :width="plotWidth"
        :height="STRIP_H"
      />
      <!-- Selection window over the waveform. -->
      <rect
        class="graphing-graph-brush__window"
        :x="winLeftPx"
        :y="STRIP_TOP"
        :width="Math.max(0, winRightPx - winLeftPx)"
        :height="STRIP_H"
      />
      <!-- Teal move-bar (drag to pan), below the waveform. -->
      <rect
        class="graphing-graph-brush__bar"
        :x="winLeftPx"
        :y="BAR_Y"
        :width="Math.max(0, winRightPx - winLeftPx)"
        :height="BAR_H"
        rx="6"
      />
      <!-- Each window edge: a full-height border line with a small centred resize handle. -->
      <g v-for="(handle, i) in edgeHandles" :key="`handle-${i}`">
        <line
          class="graphing-graph-brush__edge"
          :x1="handle.edgeX"
          :x2="handle.edgeX"
          :y1="EDGE_TOP"
          :y2="EDGE_BOTTOM"
        />
        <rect
          class="graphing-graph-brush__handle"
          :x="handle.rectX"
          :y="HANDLE_TOP"
          :width="HANDLE_W"
          :height="HANDLE_H"
          rx="2"
        />
        <line
          v-for="(gx, k) in handle.grips"
          :key="`grip-${i}-${k}`"
          class="graphing-graph-brush__grip"
          :x1="gx"
          :x2="gx"
          :y1="HANDLE_GRIP_Y1"
          :y2="HANDLE_GRIP_Y2"
        />
      </g>

      <!-- Overview extent (the time range the strip covers), bottom-left. Stood down while
           dragging, where the preview below occupies the same row. -->
      <text v-if="!dragging" class="graphing-graph-brush__range" :x="plotLeft + 2" :y="LABEL_Y">
        {{ rangeLabel }}
      </text>
    </svg>

    <div
      v-if="dragging"
      class="graphing-graph-brush__preview"
      :style="{ left: `${windowLabelX}px` }"
    >
      <b>{{ windowPreview.date }}</b>
      <span class="graphing-graph-brush__preview-divider" aria-hidden="true">|</span>
      <span>{{ windowPreview.time }}</span>
    </div>
  </div>
</template>

<style scoped>
.graphing-graph-brush {
  position: relative;
  display: block;
  user-select: none;
}

.graphing-graph-brush__track-svg {
  display: block;
}

.graphing-graph-brush--dragging {
  cursor: grabbing;
}

.graphing-graph-brush__preview {
  position: absolute;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-2) var(--dimension-4);
  background: var(--ux-theme-1);
  border-radius: var(--border-radius);
  font-size: var(--font-size-normal);
  color: var(--font-color);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  transform: translateX(-50%);
  pointer-events: none;
}

.graphing-graph-brush__preview-divider {
  color: var(--font-color-dimmed);
}

.graphing-graph-brush__track {
  fill: var(--ux-theme-1);
  stroke: var(--graphing-brush-track-stroke);
  shape-rendering: crispedges;
  cursor: grab;
}

.graphing-graph-brush__area {
  fill-opacity: 0.6;
  stroke: none;
}

.graphing-graph-brush__waveform--dimmed {
  opacity: 0.4;
}

.graphing-graph-brush__hit-area {
  fill: transparent;
  cursor: pointer;
  pointer-events: all;
}

.graphing-graph-brush__window {
  fill: transparent;
  stroke: var(--ux-theme-7, #b0b0b0);
  stroke-opacity: 0.4;
  shape-rendering: crispedges;
  cursor: grab;
}

.graphing-graph-brush__bar {
  fill: var(--color-corporate-green-50);
  stroke: var(--graphing-brush-bar-stroke);
  cursor: grab;
}

.graphing-graph-brush__bar:hover {
  fill: color-mix(in srgb, var(--color-corporate-green-50) 70%, var(--white));
}

.graphing-graph-brush--dragging .graphing-graph-brush__track,
.graphing-graph-brush--dragging .graphing-graph-brush__hit-area,
.graphing-graph-brush--dragging .graphing-graph-brush__window,
.graphing-graph-brush--dragging .graphing-graph-brush__bar {
  cursor: grabbing;
}

.graphing-graph-brush__edge {
  stroke: var(--toggle-button-group-border-color);
  stroke-width: 1;
  stroke-opacity: 0.5;
  shape-rendering: crispedges;
  pointer-events: none;
}

.graphing-graph-brush__handle {
  fill: var(--toggle-button-group-inactive-bg-color);
  stroke: var(--toggle-button-group-border-color);
  cursor: ew-resize;
}

.graphing-graph-brush__handle:hover {
  fill: color-mix(in srgb, var(--toggle-button-group-inactive-bg-color) 70%, var(--white));
}

.graphing-graph-brush__grip {
  stroke: var(--font-color);
  stroke-opacity: 0.8;
  pointer-events: none;
}

.graphing-graph-brush__range {
  fill: var(--font-color);
  font-size: var(--font-size-normal);
  opacity: 0.7;
  pointer-events: none;
}

body[data-theme='facelift'] .graphing-graph-brush {
  --graphing-brush-track-stroke: var(--color-mid-grey-10);
  --graphing-brush-bar-stroke: var(--color-corporate-green-70);
}

body[data-theme='modern-dark'] .graphing-graph-brush {
  --graphing-brush-track-stroke: var(--color-mid-grey-90);
  --graphing-brush-bar-stroke: var(--color-corporate-green-50);
}
</style>
