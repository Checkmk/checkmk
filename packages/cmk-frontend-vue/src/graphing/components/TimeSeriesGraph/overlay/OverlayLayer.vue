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

const overlayCanvas = ref<HTMLCanvasElement | null>(null)

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
    drawPinLine(ctx, props.pinX, props.plotHeight)
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
    drawFocusDots(ctx, dots)
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
</style>
