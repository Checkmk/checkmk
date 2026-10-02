<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import { computed, ref, useTemplateRef } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { LinkProperties, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

import {
  type HexagonGrid,
  type HexagonStyle,
  hexagonGrid,
  hexagonPath,
  hostIndexAt
} from './hexagon'

export interface HexagonShape {
  style: HexagonStyle
  scale: number
}

export interface HexagonCell {
  label: string
  outer: HexagonShape
  inner: HexagonShape | null
  links: ResolvedLink[]
  linkProperties: LinkProperties
}

const props = defineProps<{
  label: string
  cells: readonly HexagonCell[]
  width: number
  height: number
  maxBoxWidth: number
  filters: VisualContext
  interactive: boolean
}>()

defineSlots<{ tooltip(props: { index: number }): unknown }>()

const grid = computed(() =>
  hexagonGrid(props.cells.length, props.width, props.height, {
    layout: 'hosts',
    maxBoxWidth: props.maxBoxWidth
  })
)

function mergedLayer(
  layout: HexagonGrid,
  shapes: readonly (HexagonShape | null)[]
): [HexagonStyle, string][] {
  const merged = new Map<HexagonStyle, string[]>()
  shapes.forEach((shape, index) => {
    if (shape === null) {
      return
    }
    const parts = merged.get(shape.style) ?? []
    parts.push(hexagonPath(layout.radius * shape.scale, layout.centers[index]!))
    merged.set(shape.style, parts)
  })
  return [...merged].map(([style, parts]) => [style, parts.join('')])
}

const paths = computed(() => {
  const layout = grid.value
  if (layout === null) {
    return []
  }
  return [
    ...mergedLayer(
      layout,
      props.cells.map((cell) => cell.outer)
    ),
    ...mergedLayer(
      layout,
      props.cells.map((cell) => cell.inner)
    )
  ].map(([style, path], index) => ({ key: index, path, style }))
})

const hovered = ref<{ index: number; pointer: CmkPointerTooltipPointer } | null>(null)

const hoveredBox = computed(() => {
  const layout = grid.value
  const hover = hovered.value
  const cell = hover === null ? undefined : props.cells[hover.index]
  const center = hover === null ? undefined : layout?.centers[hover.index]
  if (layout === null || hover === null || cell === undefined || center === undefined) {
    return null
  }
  return {
    index: hover.index,
    cell,
    x: center.x - layout.boxWidth / 2,
    y: center.y - layout.boxHeight / 2,
    width: layout.boxWidth,
    height: layout.boxHeight
  }
})

const area = useTemplateRef<SVGRectElement>('area')

function track(event: PointerEvent): void {
  const layout = grid.value
  const origin = area.value?.getBoundingClientRect()
  if (layout === null || origin === undefined) {
    return
  }
  const index = hostIndexAt(layout, event.clientX - origin.left, event.clientY - origin.top)
  hovered.value =
    index === null ? null : { index, pointer: { clientX: event.clientX, clientY: event.clientY } }
}
</script>

<template>
  <svg
    role="figure"
    class="db-hexagon-grid-figure"
    :aria-label="label"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <g @pointermove="track" @pointerleave="hovered = null">
      <rect ref="area" :width="width" :height="height" fill="transparent" />
      <path
        v-for="{ key, path, style } in paths"
        :key="key"
        :d="path"
        :style="{
          fill: style.color,
          fillOpacity: style.fillOpacity,
          stroke: style.color,
          strokeOpacity: style.strokeOpacity
        }"
        pointer-events="none"
      />
      <ContextualLinkTrigger
        v-if="hoveredBox"
        :links="hoveredBox.cell.links"
        :link-properties="hoveredBox.cell.linkProperties"
        :filters="filters"
        :interactive="interactive"
      >
        <rect
          :x="hoveredBox.x"
          :y="hoveredBox.y"
          :width="hoveredBox.width"
          :height="hoveredBox.height"
          :aria-label="hoveredBox.cell.label"
          fill="transparent"
        />
      </ContextualLinkTrigger>
    </g>
  </svg>
  <CmkPointerTooltip :pointer="hovered?.pointer ?? null" @dismiss="hovered = null">
    <slot v-if="hoveredBox" name="tooltip" :index="hoveredBox.index" />
  </CmkPointerTooltip>
</template>

<style scoped>
.db-hexagon-grid-figure {
  display: block;
}
</style>
