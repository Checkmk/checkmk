<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, inject } from 'vue'

import { useMetricUnits } from '@/maps/map/composables/useMetricUnits'
import { usePerfometer } from '@/maps/map/composables/usePerfometer'
import { CANVAS_SCALE } from '@/maps/map/static/composables/useCanvasViewport'
import type { MapElement, ObjectState } from '@/maps/types/api'
import { renderMetricValue } from '@/maps/utils/metricFormat'
import { getMetric, parsePerfData, utilColor, utilPercent } from '@/maps/utils/perf'
import { stateColor } from '@/maps/utils/stateColors'

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  editMode: boolean
  dragCoords?: {
    x: number
    y: number
    x2: number
    y2: number
    mid_x?: number | null
    mid_y?: number | null
  }
  // Resolved positions for endpoints bound to an object (sticky connectors).
  // An active drag still wins so the operator sees the endpoint move.
  boundCoords?: { x?: number; y?: number; x2?: number; y2?: number }
  connectionId?: string | null
}>()

defineEmits<{
  'line-drag-start': [event: MouseEvent, mode: 'move' | 'start' | 'end' | 'mid']
  'context-menu': [event: MouseEvent]
  'line-click': []
  'line-dblclick': [event: MouseEvent]
  hover: [event: MouseEvent]
  'hover-leave': []
}>()

// Injected from MapCanvas. Translates the line's native obj.x/y coords
// into display-pixel coords so strokes, arrowheads, and text labels render
// at their natural proportions inside the no-viewBox SVG (which itself sits
// at the asymmetric-stretched canvas display size).
const canvasScale = inject(
  CANVAS_SCALE,
  computed(() => ({ sx: 1, sy: 1 }))
)

const x1 = computed(
  () => (props.dragCoords?.x ?? props.boundCoords?.x ?? props.object.x) * canvasScale.value.sx
)
const y1 = computed(
  () => (props.dragCoords?.y ?? props.boundCoords?.y ?? props.object.y) * canvasScale.value.sy
)
const x2 = computed(
  () =>
    (props.dragCoords?.x2 ?? props.boundCoords?.x2 ?? props.object.x2 ?? props.object.x + 50) *
    canvasScale.value.sx
)
const y2 = computed(
  () =>
    (props.dragCoords?.y2 ?? props.boundCoords?.y2 ?? props.object.y2 ?? props.object.y + 50) *
    canvasScale.value.sy
)

const startBound = computed(() => props.boundCoords?.x !== undefined)
const endBound = computed(() => props.boundCoords?.x2 !== undefined)

// No explicit bend ⇒ geometric center, so straight lines render unchanged.
const rawMidX = computed(() => props.dragCoords?.mid_x ?? props.object.mid_x ?? null)
const rawMidY = computed(() => props.dragCoords?.mid_y ?? props.object.mid_y ?? null)
const hasMid = computed(() => rawMidX.value !== null && rawMidY.value !== null)
const midX = computed(() =>
  hasMid.value ? rawMidX.value! * canvasScale.value.sx : (x1.value + x2.value) / 2
)
const midY = computed(() =>
  hasMid.value ? rawMidY.value! * canvasScale.value.sy : (y1.value + y2.value) / 2
)

function _halfTowardMid(fromX: number, fromY: number): { ux: number; uy: number; len: number } {
  const dx = midX.value - fromX
  const dy = midY.value - fromY
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 1) {
    return { ux: 0, uy: 0, len: 0 }
  }
  return { ux: dx / len, uy: dy / len, len }
}
const half1 = computed(() => _halfTowardMid(x1.value, y1.value))
const half2 = computed(() => _halfTowardMid(x2.value, y2.value))

// Bound-endpoint handles are nudged ~18px inward along the line so they clear
// the connected icon; unbound handles sit exactly on the endpoint.
const HANDLE_NUDGE = 18
function _nudge(
  px: number,
  py: number,
  tx: number,
  ty: number,
  on: boolean
): { x: number; y: number } {
  if (!on) {
    return { x: px, y: py }
  }
  const dx = tx - px
  const dy = ty - py
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 1) {
    return { x: px, y: py }
  }
  const d = Math.min(HANDLE_NUDGE, len / 2)
  return { x: px + (dx / len) * d, y: py + (dy / len) * d }
}
const handle1 = computed(() =>
  _nudge(
    x1.value,
    y1.value,
    hasMid.value ? midX.value : x2.value,
    hasMid.value ? midY.value : y2.value,
    startBound.value
  )
)
const handle2 = computed(() =>
  _nudge(
    x2.value,
    y2.value,
    hasMid.value ? midX.value : x1.value,
    hasMid.value ? midY.value : y1.value,
    endBound.value
  )
)

const lineColor = computed(() => props.object.line_color ?? stateColor(props.state?.state))
const lineColorBorder = computed(() => props.object.line_color_border ?? null)

const isDashed = computed(() => props.object.line_style === 'dashed')
const isArrowInward = computed(() => props.object.line_style === 'arrow_inward')
// Color the line by inbound/outbound utilization gradient instead of state color.
const useWeatherColor = computed(
  () =>
    props.object.line_weather_color === true &&
    !!(props.object.host_name && props.object.service_description)
)
// Effective stroke / fill color: utilization-based when weather coloring is
// enabled and live, otherwise the configured/state-derived line color.
const effectiveLineColor = computed(() => (useWeatherColor.value ? wmColor.value : lineColor.value))

// Per-line stroke width. Falls back to a sensible default per style:
// 6 for weather-colored lines (heavier visual weight), 2 otherwise.
const strokeWidth = computed(() => props.object.line_width ?? (useWeatherColor.value ? 6 : 2))
const strokeWidthBorder = computed(() => strokeWidth.value + 2)
const hasEndArrow = computed(
  () => props.object.line_style === 'arrow_end' || props.object.line_style === 'arrow_both'
)
const hasStartArrow = computed(
  () => props.object.line_style === 'arrow_start' || props.object.line_style === 'arrow_both'
)

// Arrowhead size scales with stroke width so a 15-px line still has a visibly
// distinct triangle, not a tip swallowed by the round line cap.
const arrowLen = computed(() => Math.max(12, strokeWidth.value * 2.4))
const arrowWidth = computed(() => Math.max(6, strokeWidth.value * 1.4))

function arrowPoints(tx: number, ty: number, fx: number, fy: number): string {
  const angle = Math.atan2(ty - fy, tx - fx)
  const len = arrowLen.value
  const w = arrowWidth.value
  const p1x = tx - len * Math.cos(angle) + w * Math.sin(angle)
  const p1y = ty - len * Math.sin(angle) - w * Math.cos(angle)
  const p2x = tx - len * Math.cos(angle) - w * Math.sin(angle)
  const p2y = ty - len * Math.sin(angle) + w * Math.cos(angle)
  return `${tx},${ty} ${p1x},${p1y} ${p2x},${p2y}`
}

// Trim an endpoint inward (toward the bend/other end) so an arrowhead's stroke
// doesn't run through its own triangle. Bound endpoints already sit on the
// connected object's edge (MapCanvas.boundCoordsFor), so no extra inset is
// needed there — the stroke meets the icon border directly.
function _trimPoint(
  px: number,
  py: number,
  tx: number,
  ty: number,
  dist: number
): { x: number; y: number } {
  if (dist <= 0) {
    return { x: px, y: py }
  }
  const dx = tx - px
  const dy = ty - py
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 1) {
    return { x: px, y: py }
  }
  const d = Math.min(dist, len - 1)
  return { x: px + (dx / len) * d, y: py + (dy / len) * d }
}
const startTrimDist = computed(() => (hasStartArrow.value ? arrowLen.value * 0.6 : 0))
const endTrimDist = computed(() => (hasEndArrow.value ? arrowLen.value * 0.6 : 0))
const trimmedStart = computed(() => {
  const p = _trimPoint(
    x1.value,
    y1.value,
    hasMid.value ? midX.value : x2.value,
    hasMid.value ? midY.value : y2.value,
    startTrimDist.value
  )
  return { x1: p.x, y1: p.y }
})
const trimmedEnd = computed(() => {
  const p = _trimPoint(
    x2.value,
    y2.value,
    hasMid.value ? midX.value : x1.value,
    hasMid.value ? midY.value : y1.value,
    endTrimDist.value
  )
  return { x2: p.x, y2: p.y }
})

const fillPolyline = computed(() => {
  const s = trimmedStart.value
  const e = trimmedEnd.value
  const ends = `${s.x1},${s.y1} ${e.x2},${e.y2}`
  return hasMid.value ? `${s.x1},${s.y1} ${midX.value},${midY.value} ${e.x2},${e.y2}` : ends
})
const borderPolyline = computed(() => {
  const s = trimmedStart.value
  const e = trimmedEnd.value
  const ends = `${s.x1},${s.y1} ${e.x2},${e.y2}`
  return hasMid.value ? `${s.x1},${s.y1} ${midX.value},${midY.value} ${e.x2},${e.y2}` : ends
})
const hitPolyline = computed(() => {
  const s = trimmedStart.value
  const e = trimmedEnd.value
  return hasMid.value
    ? `${s.x1},${s.y1} ${midX.value},${midY.value} ${e.x2},${e.y2}`
    : `${s.x1},${s.y1} ${e.x2},${e.y2}`
})

// A head arrow aligns with its own segment: it points away from the bend when
// one is set, otherwise away from the opposite endpoint.
const endArrowFrom = computed(() =>
  hasMid.value ? { x: midX.value, y: midY.value } : { x: x1.value, y: y1.value }
)
const startArrowFrom = computed(() =>
  hasMid.value ? { x: midX.value, y: midY.value } : { x: x2.value, y: y2.value }
)

// Dash pattern scales with stroke width — a fixed "6 4" pattern collapses to
// solid blocks once the line gets thicker than the dash length.
const dashArray = computed(() => {
  if (!isDashed.value) {
    return undefined
  }
  const w = strokeWidth.value
  return `${(w * 2.5).toFixed(1)} ${(w * 1.6).toFixed(1)}`
})

// NagVis arrow geometry: head length and half-width both 2x the full stroke
// (= 4x its half-width line_width), tips meeting at the midpoint.
const INWARD_GAP = 1
const inwardArrowLen = computed(() => Math.max(8, strokeWidth.value * 2.0))

// Two inward-pointing triangles meeting near the midpoint, each riding its own
// half-segment. Collinear halves (no bend) reduce to the prior straight pair.
function _inwardTriangle(u: { ux: number; uy: number }, arrowLen: number, arrowW: number): string {
  const gap = INWARD_GAP
  const tipX = midX.value - u.ux * gap
  const tipY = midY.value - u.uy * gap
  const baseX = midX.value - u.ux * (gap + arrowLen)
  const baseY = midY.value - u.uy * (gap + arrowLen)
  const perpX = -u.uy * arrowW
  const perpY = u.ux * arrowW
  return `${tipX},${tipY} ${baseX + perpX},${baseY + perpY} ${baseX - perpX},${baseY - perpY}`
}

function midpointArrows(): { left: string; right: string } | null {
  const a1 = half1.value
  const a2 = half2.value
  const arrowLen = inwardArrowLen.value
  const arrowW = Math.max(5, strokeWidth.value)
  // Per half this equals the prior straight-line ``len >= 2*arrowLen + 6``.
  if (a1.len < arrowLen + 3 || a2.len < arrowLen + 3) {
    return null
  }
  return {
    left: _inwardTriangle(a1, arrowLen, arrowW),
    right: _inwardTriangle(a2, arrowLen, arrowW)
  }
}

const midArrows = computed(() => midpointArrows())

// Endpoints for the two half-lines: each stops at its arrowhead base so the
// stroke doesn't run through the meeting arrows.
const inwardSegments = computed(() => {
  const a1 = half1.value
  const a2 = half2.value
  if (a1.len < inwardArrowLen.value + 3 || a2.len < inwardArrowLen.value + 3) {
    return null
  }
  const back = INWARD_GAP + inwardArrowLen.value
  return {
    leftX: midX.value - a1.ux * back,
    leftY: midY.value - a1.uy * back,
    rightX: midX.value - a2.ux * back,
    rightY: midY.value - a2.uy * back
  }
})

// Anchor positions for the inbound/outbound bandwidth labels.
// Placed at ~25%/75% along the line so they always sit clear of the midpoint
// arrows regardless of line length. Pure-pixel offset doesn't scale: short
// lines get cramped, long lines have labels overlapping.
const wmLabelAnchors = computed(() => {
  const dx = x2.value - x1.value
  const dy = y2.value - y1.value
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 80) {
    return null
  }
  const a1 = half1.value
  const a2 = half2.value
  // 25% of total length from midpoint, clamped so labels stay readable on
  // medium lines and don't run off the endpoints on short ones. The per-half
  // cap never bites on a straight line (each half is len/2), keeping placement
  // unchanged there.
  const offset = Math.max(40, Math.min(len * 0.25, len / 2 - 30))
  const o1 = Math.min(offset, Math.max(0, a1.len - 10))
  const o2 = Math.min(offset, Math.max(0, a2.len - 10))
  return {
    inX: midX.value - a1.ux * o1,
    inY: midY.value - a1.uy * o1,
    outX: midX.value - a2.ux * o2,
    outY: midY.value - a2.uy * o2
  }
})

// Approximate label-box width from character count. Used to size the
// background rect under each weathermap label without measuring real text.
function _labelBoxWidth(label: string): number {
  return Math.max(40, label.length * 7 + 14)
}

// Per-utilization color gradient state — driven by inbound/outbound metrics
// when weather coloring is on. Even when off, these still feed the perfdata
// labels (which can be enabled independently).
const gradientId = computed(() => `wm-grad-${props.object.id}`)

const wmMetrics = computed(() => parsePerfData(props.state?.perf_data ?? ''))
const wmMetricIn = computed(() =>
  getMetric(wmMetrics.value, props.object.weathermap_metric ?? undefined)
)
const wmMetricOut = computed(() =>
  getMetric(wmMetrics.value, props.object.weathermap_metric_out ?? undefined)
)
const wmPct = computed(() => {
  const m = wmMetricIn.value ?? wmMetricOut.value
  return m ? utilPercent(m) : 0
})
const wmColor = computed(() => utilColor(wmPct.value))
const wmColorIn = computed(() =>
  wmMetricIn.value ? utilColor(utilPercent(wmMetricIn.value)) : wmColor.value
)
const wmColorOut = computed(() =>
  wmMetricOut.value ? utilColor(utilPercent(wmMetricOut.value)) : wmColor.value
)
// Only render the in→out gradient when a distinct outbound metric is
// configured; with only one metric, a fade-out looks like a rendering bug.
const hasDirectionalGradient = computed(
  () =>
    !!props.object.weathermap_metric_out &&
    props.object.weathermap_metric_out !== props.object.weathermap_metric
)

// userSpaceOnUse gradient, so arrow_inward's two half-lines can share the same
// url() reference and each still show the correct slice.
const fillStroke = computed(() =>
  useWeatherColor.value && hasDirectionalGradient.value
    ? `url(#${gradientId.value})`
    : effectiveLineColor.value
)

const showsPerfdataLabels = computed(
  () =>
    props.object.line_perfdata_label !== null &&
    props.object.line_perfdata_label !== undefined &&
    props.object.line_perfdata_label !== 'none'
)

function _fmtMetric(m: ReturnType<typeof getMetric>): string {
  if (!m) {
    return ''
  }
  return renderMetricValue(m.value, lineMetricUnits.value[m.label], m.unit)
}

// CMK-formatted bandwidth strings & utilization via the GUI perfometer (when
// host+service set). It applies the proper Metric.unit (kbit/s, …) and
// computes percentages from the plugin's focus_range — which the raw
// perfdata's max field often doesn't carry for interface checks.
const lineBinding = {
  connectionId: () => props.connectionId,
  hostName: () => props.object.host_name,
  serviceDescription: () => props.object.service_description,
  perfData: () => props.state?.perf_data,
  checkCommand: () => props.state?.check_command,
  enabled: () => showsPerfdataLabels.value
}
const cmkPerfData = usePerfometer(lineBinding)
// Registered display units for the raw-metric fallback labels.
const lineMetricUnits = useMetricUnits(lineBinding)

// The two direction halves for separate rendering on each side of the
// midpoint arrows: a bidirectional perfometer yields in/out, a plain one
// only the first half.
const cmkSplit = computed<[string | null, string | null]>(() => {
  const sides = cmkPerfData.value?.sides ?? []
  return [sides[0]?.label ?? null, sides[1]?.label ?? null]
})

const cmkPcts = computed<[number | null, number | null]>(() => {
  const sides = cmkPerfData.value?.sides ?? []
  return [sides[0]?.pct ?? null, sides[1]?.pct ?? null]
})

// Format a label for the chosen perfdata mode. 'percent' prefers the CMK
// perfometer utilization (uses plugin focus_range / interface speed), falling
// back to client-side utilPercent which only works when perfdata has max set.
function _fmtLabel(
  m: ReturnType<typeof getMetric>,
  cmkValue: string | null,
  cmkPct: number | null
): string {
  if (!m) {
    return ''
  }
  const mode = props.object.line_perfdata_label ?? 'none'
  if (mode === 'none') {
    return ''
  }
  const pct = cmkPct ?? utilPercent(m)
  if (mode === 'percent') {
    return `${pct.toFixed(0)}%`
  }
  const value = cmkValue ?? _fmtMetric(m)
  if (mode === 'both') {
    return `${value} (${pct.toFixed(0)}%)`
  }
  return value // 'bandwidth'
}

const wmLabelIn = computed(() => _fmtLabel(wmMetricIn.value, cmkSplit.value[0], cmkPcts.value[0]))
const wmLabelOut = computed(() => _fmtLabel(wmMetricOut.value, cmkSplit.value[1], cmkPcts.value[1]))
// Fallback: a single value below the midpoint when neither in/out has a real
// metric to render but the mode is non-none — used as a state hint.
const wmLabelSingle = computed(() => {
  if (!showsPerfdataLabels.value) {
    return ''
  }
  if (wmLabelIn.value || wmLabelOut.value) {
    return ''
  }
  return ''
})
</script>

<template>
  <g :data-object-id="object.id">
    <!-- Invisible fat hit-area: always for right-click, move-cursor only in edit mode -->
    <polyline
      :points="hitPolyline"
      fill="none"
      stroke="transparent"
      stroke-width="12"
      :style="editMode ? 'cursor: move' : 'cursor: pointer'"
      @mousedown.prevent.stop="editMode ? $emit('line-drag-start', $event, 'move') : undefined"
      @contextmenu.prevent.stop="$emit('context-menu', $event)"
      @click.stop="$emit('line-click')"
      @dblclick.stop="$emit('line-dblclick', $event)"
      @mouseenter="!editMode && $emit('hover', $event)"
      @mouseleave="!editMode && $emit('hover-leave')"
    />

    <!-- In→Out utilization gradient. Only meaningful when a second
             outbound metric is configured; otherwise we fall back to a solid
             stroke (see :stroke binding below) to avoid a misleading fade. -->
    <defs v-if="useWeatherColor && hasDirectionalGradient">
      <linearGradient
        :id="gradientId"
        gradientUnits="userSpaceOnUse"
        :x1="x1"
        :y1="y1"
        :x2="x2"
        :y2="y2"
      >
        <stop offset="0%" :stop-color="wmColorIn" />
        <stop offset="100%" :stop-color="wmColorOut" />
      </linearGradient>
    </defs>
    <!-- arrow_inward draws as two half-lines that each stop at their
             midpoint arrowhead base, mirroring NagVis' two-segment rendering
             so the stroke doesn't run through the meeting arrows. -->
    <template v-if="isArrowInward && inwardSegments">
      <line
        v-if="lineColorBorder && !useWeatherColor"
        :x1="x1"
        :y1="y1"
        :x2="inwardSegments.leftX"
        :y2="inwardSegments.leftY"
        :stroke="lineColorBorder"
        :stroke-width="strokeWidthBorder"
        stroke-linecap="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
      <line
        v-if="lineColorBorder && !useWeatherColor"
        :x1="x2"
        :y1="y2"
        :x2="inwardSegments.rightX"
        :y2="inwardSegments.rightY"
        :stroke="lineColorBorder"
        :stroke-width="strokeWidthBorder"
        stroke-linecap="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
      <line
        :x1="x1"
        :y1="y1"
        :x2="inwardSegments.leftX"
        :y2="inwardSegments.leftY"
        :stroke="fillStroke"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
      <line
        :x1="x2"
        :y1="y2"
        :x2="inwardSegments.rightX"
        :y2="inwardSegments.rightY"
        :stroke="fillStroke"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
    </template>
    <template v-else>
      <polyline
        v-if="lineColorBorder && !useWeatherColor"
        :points="borderPolyline"
        fill="none"
        :stroke="lineColorBorder"
        :stroke-width="strokeWidthBorder"
        stroke-linecap="round"
        stroke-linejoin="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
      <polyline
        :points="fillPolyline"
        fill="none"
        :stroke="fillStroke"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        stroke-linejoin="round"
        :stroke-dasharray="dashArray"
        pointer-events="none"
      />
    </template>
    <polygon
      v-if="hasEndArrow"
      :points="arrowPoints(x2, y2, endArrowFrom.x, endArrowFrom.y)"
      :fill="effectiveLineColor"
      pointer-events="none"
    />
    <polygon
      v-if="hasStartArrow"
      :points="arrowPoints(x1, y1, startArrowFrom.x, startArrowFrom.y)"
      :fill="effectiveLineColor"
      pointer-events="none"
    />
    <!-- Inward arrows: two triangles meeting at the midpoint. -->
    <template v-if="isArrowInward && midArrows">
      <polygon :points="midArrows.left" :fill="effectiveLineColor" pointer-events="none" />
      <polygon :points="midArrows.right" :fill="effectiveLineColor" pointer-events="none" />
    </template>
    <!-- In/out perfdata labels in boxed badges flanking the midpoint
             at 25% / 75% along the line. -->
    <g v-if="wmLabelAnchors && wmLabelIn" pointer-events="none">
      <rect
        :x="wmLabelAnchors.inX - _labelBoxWidth(wmLabelIn) / 2"
        :y="wmLabelAnchors.inY - 10"
        :width="_labelBoxWidth(wmLabelIn)"
        height="20"
        rx="3"
        fill="white"
        :stroke="effectiveLineColor"
        stroke-width="1.5"
      />
      <text
        :x="wmLabelAnchors.inX"
        :y="wmLabelAnchors.inY"
        text-anchor="middle"
        dominant-baseline="middle"
        font-weight="700"
        :style="{ fill: '#000', fontSize: '11px' }"
        >{{ wmLabelIn }}</text
      >
    </g>
    <g v-if="wmLabelAnchors && wmLabelOut" pointer-events="none">
      <rect
        :x="wmLabelAnchors.outX - _labelBoxWidth(wmLabelOut) / 2"
        :y="wmLabelAnchors.outY - 10"
        :width="_labelBoxWidth(wmLabelOut)"
        height="20"
        rx="3"
        fill="white"
        :stroke="effectiveLineColor"
        stroke-width="1.5"
      />
      <text
        :x="wmLabelAnchors.outX"
        :y="wmLabelAnchors.outY"
        text-anchor="middle"
        dominant-baseline="middle"
        font-weight="700"
        :style="{ fill: '#000', fontSize: '11px' }"
        >{{ wmLabelOut }}</text
      >
    </g>
    <!-- Single-direction fallback when only one perfdata label fits. -->
    <text
      v-if="wmLabelSingle"
      :x="midX"
      :y="midY + 16"
      text-anchor="middle"
      font-weight="700"
      :style="{
        fontSize: '13px',
        fill: effectiveLineColor,
        paintOrder: 'stroke',
        stroke: 'var(--ux-theme-1)',
        strokeWidth: '4px',
        strokeLinejoin: 'round'
      }"
      pointer-events="none"
      >{{ wmLabelSingle }}</text
    >

    <text
      v-if="props.object.label?.show && props.object.label?.text"
      :x="midX"
      :y="midY - 10"
      text-anchor="middle"
      font-weight="500"
      :style="{
        fontSize: `${props.object.label?.size ?? 11}px`,
        fill: props.object.label?.color ?? '#e4e4e7',
        paintOrder: 'stroke',
        stroke: 'rgb(0 0 0 / 80%)',
        strokeWidth: '3px',
        strokeLinejoin: 'round'
      }"
      pointer-events="none"
      >{{ props.object.label?.text }}</text
    >

    <!-- Edit handles. A bound endpoint's handle is nudged inward along the line
         so it stops covering the connected icon — leaving the icon's centre
         grabbable (drag the icon → line follows; drag this handle → detach). -->
    <template v-if="editMode">
      <circle
        :cx="handle1.x"
        :cy="handle1.y"
        r="7"
        :fill="startBound ? '#22c55e' : '#3b82f6'"
        fill-opacity="0.85"
        stroke="white"
        stroke-width="1.5"
        style="cursor: grab"
        @mousedown.prevent.stop="$emit('line-drag-start', $event, 'start')"
      />
      <circle
        :cx="handle2.x"
        :cy="handle2.y"
        r="7"
        :fill="endBound ? '#22c55e' : '#3b82f6'"
        fill-opacity="0.85"
        stroke="white"
        stroke-width="1.5"
        style="cursor: grab"
        @mousedown.prevent.stop="$emit('line-drag-start', $event, 'end')"
      />
      <!-- Bend handle: hollow when no explicit bend yet (dragging adds one). -->
      <circle
        :cx="midX"
        :cy="midY"
        r="6"
        :fill="hasMid ? '#3b82f6' : 'white'"
        fill-opacity="0.85"
        stroke="#3b82f6"
        stroke-width="1.5"
        style="cursor: grab"
        @mousedown.prevent.stop="$emit('line-drag-start', $event, 'mid')"
      />
    </template>
  </g>
</template>
