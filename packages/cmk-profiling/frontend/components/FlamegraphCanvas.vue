<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import type { CallerInfo, FlamegraphNode } from '../types'
import {
  HIGHLIGHT_STROKE_WIDTH,
  RECT_HOVER_OVERLAY,
  RECT_LABEL_COLOR_PRIMARY,
  RECT_LABEL_COLOR_SECONDARY,
  RECT_THIN_BORDER,
  THIN_BORDER_WIDTH,
  nameColor
} from '../utils/flamegraph-colors'
import { hitTest, layoutFlamegraph } from '../utils/flamegraph-layout'
import { formatCalls, formatDuration, formatPercent } from '../utils/format'

const props = defineProps<{
  tree: FlamegraphNode
  totalTime: number
  searchQuery: string
  highlightFunction: string
  callersMap: Map<string, CallerInfo[]>
  functionPaths: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'select-function', name: string): void
  (e: 'zoom-out'): void
}>()

const { _t } = usei18n()

interface TooltipState {
  x: number
  y: number
  name: string
  fullPath: string
  selfText: string
  totalText: string
  callers: CallerInfo[]
}

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const canvasWrapRef = ref<HTMLDivElement | null>(null)

const tooltip = ref<TooltipState | null>(null)
const hoverName = ref('')
const depthLimitStr = ref<string | null>('10')

const depthLimit = computed(() => {
  const n = Number(depthLimitStr.value)
  return n === 0 ? Infinity : n || 10
})

const CANVAS_LOGICAL_WIDTH = 1600
const CHAR_WIDTH = 7
const TIME_CHAR_WIDTH = 6

interface ThemeTokens {
  highlightStroke: string
  fontNormal: string
  fontSmall: string
}

// Canvas 2D can't resolve CSS var() references, so pull the tokens from the
// container and cache the resolved values. The hard-coded fallback matches the
// corporate-green used by --interactive-accent in both themes — it
// keeps the highlight outline visible even if the var is unset (e.g. styles
// not yet applied on first paint).
const HIGHLIGHT_STROKE_FALLBACK = '#2e8540'

function readThemeTokens(el: HTMLElement): ThemeTokens {
  const style = getComputedStyle(el)
  return {
    highlightStroke:
      style.getPropertyValue('--interactive-accent').trim() || HIGHLIGHT_STROKE_FALLBACK,
    fontNormal: `${style.getPropertyValue('--font-size-normal').trim()} sans-serif`,
    fontSmall: `${style.getPropertyValue('--font-size-small').trim()} sans-serif`
  }
}

const depthOptions = [
  { name: '5', title: untranslated('5') },
  { name: '10', title: untranslated('10') },
  { name: '15', title: untranslated('15') },
  { name: '20', title: untranslated('20') },
  { name: '0', title: _t('All') }
]

// Layout is recomputed when either the tree or the selected depth changes:
// a finite depth clips deeper rects at layout time so the scroll area stays
// bounded at the chosen depth; "All" (Infinity) renders the whole tree.
const fullLayout = computed(() =>
  layoutFlamegraph(props.tree, CANVAS_LOGICAL_WIDTH, depthLimit.value)
)

const rects = computed(() => fullLayout.value.rects)
const canvasHeight = computed(() => fullLayout.value.height)

// The canvas is a visual representation of data that the HotspotsTable
// renders accessibly. Provide a summary label for screen readers.
const canvasAriaLabel = computed(() => {
  const rectCount = rects.value.length
  const timeText = formatDuration(props.totalTime)
  return _t('Flamegraph of %1 functions, total time %2 — see hotspots table for details.')
    .replace('%1', rectCount.toLocaleString())
    .replace('%2', timeText)
})

// Wrapper height is capped at the depth-10 viewport so the hotspots table
// below always stays visible. For depth ≤ 10 the canvas fits exactly; for
// depth > 10 (or "All") the viewport stays capped and scrolls internally.
const DEPTH_CAP = 10
const DEPTH_CAP_HEIGHT = 10 + DEPTH_CAP * 50

const wrapHeight = computed(() => {
  const limit = depthLimit.value
  if (limit === Infinity || limit > DEPTH_CAP) {
    return DEPTH_CAP_HEIGHT
  }
  return 10 + limit * 50
})

const wrapOverflow = computed(() => {
  const limit = depthLimit.value
  return limit === Infinity || limit > DEPTH_CAP ? 'auto' : 'hidden'
})

let resizeObserver: ResizeObserver | null = null

function draw() {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }

  const container = containerRef.value
  const displayWidth = container ? container.clientWidth : canvas.width
  const newHeight = canvasHeight.value

  // Reassigning canvas.width/height is expensive (buffer reallocation, GPU sync).
  // Only do it when dimensions actually changed; otherwise clearRect is much faster.
  if (canvas.width !== displayWidth || canvas.height !== newHeight) {
    canvas.width = displayWidth
    canvas.height = newHeight
  } else {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
  }

  const scale = displayWidth / CANVAS_LOGICAL_WIDTH
  const tokens = readThemeTokens(container ?? canvas)

  const query = props.searchQuery.toLowerCase()
  const highlight = props.highlightFunction
  const hoveredName = hoverName.value
  const hasQuery = query.length >= 2

  // A search dims every non-matching frame so matches stand out. A highlight
  // (from a graph click or a hotspots-table pick that re-roots the graph to the
  // picked function) only outlines its frame — the whole stack stays visible.
  //
  // Pass 1: fill all rects (skip subpixel rects). Group by alpha so we minimize
  // state changes. Using fillRect is significantly faster than path-based fill.
  ctx.globalAlpha = 1.0
  for (const rect of rects.value) {
    const sw = rect.width * scale
    if (sw < 1) {
      continue
    }
    const sx = rect.x * scale
    const isSearchMatch = hasQuery && rect.name.toLowerCase().includes(query)
    const isDimmed = hasQuery && !isSearchMatch
    ctx.globalAlpha = isDimmed ? 0.15 : 1.0
    ctx.fillStyle = nameColor(rect.name)
    ctx.fillRect(sx, rect.y, sw, rect.height)
  }

  // Pass 2: hover overlay + strokes + labels — only for visible rects
  ctx.globalAlpha = 1.0
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (const rect of rects.value) {
    const sw = rect.width * scale
    if (sw < 1) {
      continue
    }
    const sx = rect.x * scale
    const sy = rect.y
    const sh = rect.height

    const isMatch = hasQuery && rect.name.toLowerCase().includes(query)
    const isDimmed = hasQuery && !isMatch
    const isHighlighted = highlight !== '' && rect.name === highlight
    const isHovered = hoveredName !== '' && rect.name === hoveredName

    if (isHovered && !isDimmed) {
      ctx.fillStyle = RECT_HOVER_OVERLAY
      ctx.fillRect(sx, sy, sw, sh)
    }

    if (isHighlighted || isMatch || isHovered) {
      ctx.strokeStyle = tokens.highlightStroke
      ctx.lineWidth = HIGHLIGHT_STROKE_WIDTH
      ctx.strokeRect(sx, sy, sw, sh)
    } else if (sw >= 4) {
      // Skip thin borders on very small rects — not visible anyway
      ctx.strokeStyle = RECT_THIN_BORDER
      ctx.lineWidth = THIN_BORDER_WIDTH
      ctx.strokeRect(sx, sy, sw, sh)
    }

    // Labels — only for rects wide enough to show text
    const availableWidth = sw - 16
    if (availableWidth < 10) {
      continue
    }

    ctx.globalAlpha = isDimmed ? 0.15 : 1.0
    ctx.fillStyle = RECT_LABEL_COLOR_PRIMARY
    const centerX = sx + sw / 2
    const centerY = sy + sh / 2

    ctx.font = tokens.fontNormal
    const nameMaxChars = Math.floor(availableWidth / CHAR_WIDTH)
    const label =
      rect.name.length > nameMaxChars ? `${rect.name.slice(0, nameMaxChars - 1)}…` : rect.name

    const timeText = formatDuration(rect.totalTime)
    const timeFits = timeText.length * TIME_CHAR_WIDTH <= availableWidth
    if (sh >= 30 && timeFits) {
      ctx.fillText(label, centerX, centerY - 8)
      ctx.font = tokens.fontSmall
      ctx.fillStyle = RECT_LABEL_COLOR_SECONDARY
      ctx.fillText(timeText, centerX, centerY + 8)
    } else {
      ctx.fillText(label, centerX, centerY)
    }
    ctx.globalAlpha = 1.0
  }

  ctx.textAlign = 'start'
  ctx.textBaseline = 'alphabetic'
}

function hitTestAt(event: MouseEvent): number {
  const canvas = canvasRef.value
  if (!canvas) {
    return -1
  }
  const rect = canvas.getBoundingClientRect()
  const scale = canvas.width / CANVAS_LOGICAL_WIDTH
  const px = (event.clientX - rect.left) / scale
  const py = event.clientY - rect.top
  return hitTest(rects.value, px, py)
}

function onMouseMove(event: MouseEvent) {
  const idx = hitTestAt(event)
  if (idx >= 0) {
    const r = rects.value[idx]!
    hoverName.value = r.name
    const selfPct = props.totalTime > 0 ? (r.selfTime / props.totalTime) * 100 : 0
    const totalPct = props.totalTime > 0 ? (r.totalTime / props.totalTime) * 100 : 0
    const callers = (props.callersMap.get(r.name) ?? []).slice(0, 5)

    tooltip.value = {
      x: event.clientX + 12,
      y: event.clientY - 10,
      name: r.name,
      fullPath: props.functionPaths[r.name] ?? '',
      selfText: `${formatDuration(r.selfTime)} (${formatPercent(selfPct)})`,
      totalText: `${formatDuration(r.totalTime)} (${formatPercent(totalPct)})`,
      callers
    }
  } else {
    hoverName.value = ''
    tooltip.value = null
  }
}

function onClick(event: MouseEvent) {
  const idx = hitTestAt(event)
  if (idx < 0) {
    return
  }
  const clickedRect = rects.value[idx]!
  tooltip.value = null
  // Clicking the topmost frame is "zoom out" — go back to the previous root
  // if the parent is currently zoomed in. The parent decides what to do
  // when the zoom stack is empty (typically a no-op).
  if (clickedRect.depth === 0) {
    emit('zoom-out')
    return
  }
  emit('select-function', clickedRect.name)
}

function onMouseLeave() {
  hoverName.value = ''
  tooltip.value = null
}

// Force redraw when the tree prop changes (e.g. table selection).
watch(
  () => props.tree,
  async () => {
    await nextTick()
    draw()
  }
)

// Reset the canvas-wrap scroll position when the depth changes — otherwise a
// previously-scrolled view persists when switching back to a smaller depth.
watch(depthLimit, () => {
  if (canvasWrapRef.value) {
    canvasWrapRef.value.scrollTop = 0
  }
})

watch([() => props.searchQuery, () => props.highlightFunction, rects, hoverName], async () => {
  // nextTick lets Vue commit canvasHeight to the <canvas> element first;
  // otherwise Vue's later attribute patch resets the freshly drawn pixels.
  await nextTick()
  draw()
})

onMounted(() => {
  draw()
  resizeObserver = new ResizeObserver(() => draw())
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<template>
  <div ref="containerRef" class="profiling-flamegraph-canvas">
    <div
      ref="canvasWrapRef"
      class="profiling-flamegraph-canvas__canvas-wrap"
      :style="{ height: `${wrapHeight}px`, overflowY: wrapOverflow }"
    >
      <canvas
        ref="canvasRef"
        :height="canvasHeight"
        role="img"
        :aria-label="canvasAriaLabel"
        @mousemove="onMouseMove"
        @mouseleave="onMouseLeave"
        @click="onClick"
      />
    </div>

    <!-- Depth selector (below canvas, right-aligned) -->
    <div class="profiling-flamegraph-canvas__footer">
      <span class="profiling-flamegraph-canvas__depth-label">{{ _t('Depth') }}</span>
      <CmkDropdown
        v-model="depthLimitStr"
        :options="{ type: 'fixed', suggestions: depthOptions }"
        :label="_t('Depth')"
      />
    </div>
    <!-- Pointer-only tooltip; the accessible counterpart is HotspotsTable,
         so we deliberately omit role="tooltip" / aria-live. -->
    <div
      v-if="tooltip"
      class="profiling-flamegraph-canvas__tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <div class="profiling-flamegraph-canvas__tooltip-name">{{ tooltip.name }}</div>
      <div
        v-if="tooltip.fullPath"
        class="profiling-flamegraph-canvas__tooltip-path"
        :title="tooltip.fullPath"
      >
        {{ tooltip.fullPath }}
      </div>
      <div class="profiling-flamegraph-canvas__tooltip-line">
        {{ _t('Self:') }} {{ tooltip.selfText }}
      </div>
      <div class="profiling-flamegraph-canvas__tooltip-line">
        {{ _t('Total:') }} {{ tooltip.totalText }}
      </div>
      <template v-if="tooltip.callers.length > 0">
        <div class="profiling-flamegraph-canvas__tooltip-callers-title">
          {{ _t('Called by:') }}
        </div>
        <div
          v-for="(c, i) in tooltip.callers"
          :key="i"
          class="profiling-flamegraph-canvas__tooltip-caller"
        >
          <!-- eslint-disable-next-line vue/no-bare-strings-in-template -- single-word count unit -->
          {{ c.function }} ({{ formatCalls(c.ncalls, c.primitive_calls) }} {{ _t('calls') }})
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.profiling-flamegraph-canvas {
  position: relative;
  width: 100%;
}

/* Canvas wrap: height + overflow-y set inline. For depth ≤ 10 height matches
 * content (no scroll). For depth > 10 it caps + scrolls internally. */
.profiling-flamegraph-canvas__canvas-wrap {
  /* properties set via :style */
}

.profiling-flamegraph-canvas canvas {
  display: block;
  width: 100%;
  cursor: pointer;
}

/* Footer (below canvas): Depth selector, right-aligned */
.profiling-flamegraph-canvas__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-half);
  padding: var(--spacing-half) 0;
}

.profiling-flamegraph-canvas__depth-label {
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.profiling-flamegraph-canvas__tooltip {
  position: fixed;
  z-index: var(--z-index-tooltip-offset);
  background: var(--default-tooltip-background-color);
  color: var(--default-tooltip-text-color);
  padding: var(--spacing-half) var(--spacing);
  border-radius: var(--border-radius);
  font-family: monospace;
  font-size: var(--font-size-normal);
  line-height: 1.5;
  pointer-events: none;
  white-space: nowrap;
  max-width: 600px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profiling-flamegraph-canvas__tooltip-name {
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-half);
}

.profiling-flamegraph-canvas__tooltip-path {
  font-size: var(--font-size-small);
  opacity: 0.75;
  margin-bottom: var(--spacing-half);
  overflow: hidden;
  text-overflow: ellipsis;
}

.profiling-flamegraph-canvas__tooltip-line {
  opacity: 0.8;
}

.profiling-flamegraph-canvas__tooltip-callers-title {
  margin-top: var(--spacing-half);
  font-weight: var(--font-weight-bold);
  opacity: 0.7;
  font-size: var(--font-size-small);
}

.profiling-flamegraph-canvas__tooltip-caller {
  opacity: 0.7;
  font-size: var(--font-size-small);
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
