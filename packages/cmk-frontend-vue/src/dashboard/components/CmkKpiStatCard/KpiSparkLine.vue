<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { scaleLinear } from 'd3-scale'
import { area, curveCatmullRom, line } from 'd3-shape'
import { type Ref, computed, useId } from 'vue'

const props = defineProps<{
  /** Data points to plot, oldest first. Needs at least two to render a path. */
  series: number[]
  /** Stroke / fill color, e.g. "var(--color-corporate-green-50)". */
  color: string
}>()

// The SVG is drawn in an abstract coordinate space and stretched to fit the
// card via preserveAspectRatio="none". D3 only generates the path strings here
// (Vue owns the DOM), so a fixed viewBox keeps the scaling math simple.
const VIEW_WIDTH = 100
const VIEW_HEIGHT = 40

// Unique per instance so multiple cards on one dashboard don't share a <defs> id.
const gradientId = `db-kpi-spark-line-gradient-${useId()}`

const paths: Ref<{ line: string; area: string }> = computed(() => {
  const data = props.series
  if (data.length < 2) {
    return { line: '', area: '' }
  }

  const xScale = scaleLinear()
    .domain([0, data.length - 1])
    .range([0, VIEW_WIDTH])

  const min = Math.min(...data)
  const max = Math.max(...data)
  // Pad the value range so the line never touches the very top/bottom edge.
  const padding = (max - min) * 0.15 || 1
  const yScale = scaleLinear()
    .domain([min - padding, max + padding])
    .range([VIEW_HEIGHT, 0])

  const lineGen = line<number>()
    .x((_, i) => xScale(i))
    .y((value) => yScale(value))
    .curve(curveCatmullRom.alpha(0.5))

  const areaGen = area<number>()
    .x((_, i) => xScale(i))
    .y0(VIEW_HEIGHT)
    .y1((value) => yScale(value))
    .curve(curveCatmullRom.alpha(0.5))

  return { line: lineGen(data) ?? '', area: areaGen(data) ?? '' }
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
      <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="currentColor" stop-opacity="0.35" />
        <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
      </linearGradient>
    </defs>
    <path :d="paths.area" :fill="`url(#${gradientId})`" stroke="none" />
    <path
      :d="paths.line"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</template>

<style scoped>
.db-kpi-spark-line {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
