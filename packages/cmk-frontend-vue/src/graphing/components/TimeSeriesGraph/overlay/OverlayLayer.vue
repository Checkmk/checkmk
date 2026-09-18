<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { HoverState } from '../interaction/hover'
import GraphTooltip from './GraphTooltip.vue'
import { type FocusDot, drawCrosshair, drawFocusDots, drawPinLine } from './crosshair'

const props = defineProps<{
  hoverState: HoverState | null
  plotWidth: number
  plotHeight: number
  pinX: number | null
}>()

const overlayRoot = ref<HTMLElement | null>(null)
const overlayCanvas = ref<HTMLCanvasElement | null>(null)

// Canvas takes colours as strings, so theme-dependent ones are resolved off the element
// rather than referenced. Read per draw: the value is only correct once mounted and styled.
const FOCUS_DOT_STROKE_FALLBACK = '#ffffff'
const PIN_LINE_STROKE_FALLBACK = '#15d1a0'

function resolvedColor(property: string, fallback: string): string {
  const root = overlayRoot.value
  if (!root) {
    return fallback
  }
  const resolved = getComputedStyle(root).getPropertyValue(property).trim()
  return resolved === '' ? fallback : resolved
}

function sizeCanvasToDevicePixelRatio(): void {
  const canvas = overlayCanvas.value
  if (!canvas) {
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.round(props.plotWidth * dpr)
  canvas.height = Math.round(props.plotHeight * dpr)
  canvas.style.width = `${props.plotWidth}px`
  canvas.style.height = `${props.plotHeight}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function redraw(): void {
  const canvas = overlayCanvas.value
  if (!canvas) {
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  ctx.clearRect(0, 0, props.plotWidth, props.plotHeight)
  if (props.pinX !== null) {
    drawPinLine(
      ctx,
      props.pinX,
      props.plotHeight,
      resolvedColor('--graphing-pin-line-stroke', PIN_LINE_STROKE_FALLBACK)
    )
  }
  if (props.hoverState) {
    drawCrosshair(ctx, props.hoverState.snapX, props.plotHeight)
    const dots: FocusDot[] = []
    for (const sample of props.hoverState.samples) {
      if (sample.pixelY !== null) {
        dots.push({
          x: props.hoverState.snapX,
          y: sample.pixelY,
          color: sample.color,
          closest: sample.isClosest
        })
      }
    }
    drawFocusDots(
      ctx,
      dots,
      resolvedColor('--graphing-focus-dot-stroke', FOCUS_DOT_STROKE_FALLBACK)
    )
  }
}

let dprMedia: MediaQueryList | null = null

function attachDPRWatcher(): void {
  const dpr = window.devicePixelRatio || 1
  dprMedia = window.matchMedia(`(resolution: ${dpr}dppx)`)
  dprMedia.addEventListener('change', onDPRChange, { once: true })
}

function onDPRChange(): void {
  sizeCanvasToDevicePixelRatio()
  redraw()
  attachDPRWatcher()
}

onMounted(() => {
  sizeCanvasToDevicePixelRatio()
  redraw()
  attachDPRWatcher()
})

onBeforeUnmount(() => {
  dprMedia?.removeEventListener('change', onDPRChange)
  dprMedia = null
})

watch(
  () => [props.plotWidth, props.plotHeight],
  () => {
    sizeCanvasToDevicePixelRatio()
    redraw()
  }
)

watch(() => props.hoverState, redraw)
watch(() => props.pinX, redraw)
</script>

<template>
  <div
    ref="overlayRoot"
    class="graphing-overlay-layer"
    :style="{ width: `${plotWidth}px`, height: `${plotHeight}px` }"
  >
    <canvas ref="overlayCanvas" class="graphing-overlay-layer__canvas" aria-hidden="true" />
    <GraphTooltip :hover-state="hoverState" />
  </div>
</template>

<style scoped>
.graphing-overlay-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.graphing-overlay-layer__canvas {
  position: absolute;
  top: 0;
  left: 0;
}

body[data-theme='facelift'] .graphing-overlay-layer {
  --graphing-focus-dot-stroke: var(--color-conference-grey-100);
  --graphing-pin-line-stroke: var(--color-corporate-green-70);
}

body[data-theme='modern-dark'] .graphing-overlay-layer {
  --graphing-focus-dot-stroke: var(--color-white-100);
  --graphing-pin-line-stroke: var(--color-corporate-green-50);
}
</style>
