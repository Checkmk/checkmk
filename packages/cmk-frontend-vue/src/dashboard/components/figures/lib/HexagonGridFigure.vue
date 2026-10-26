<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkPointerTooltip, {
  type CmkPointerTooltipPointer
} from 'cmk-ui-library/components/CmkPointerTooltip.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { useWidgetKeys } from 'cmk-ui-library/lib/keyboardHelp'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import { contextualLinkCount } from '@/dashboard/lib/contextualLinkUrl'
import type { LinkProperties, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

import { byKeyboard } from './byKeyboard'
import {
  type HexagonGrid,
  type HexagonStyle,
  hexagonGrid,
  hexagonPath,
  hostIndexAt,
  neighbourIndex
} from './hexagon'

const FOCUS_OUTLINE_OFFSET = 5

export interface HexagonShape {
  style: HexagonStyle
  scale: number
}

export interface HexagonCell {
  label: string
  /** What the cell's tooltip tells, so that keyboard and screen reader users learn it too. */
  description?: string
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
}>()

defineSlots<{ tooltip(props: { index: number; several: boolean }): unknown }>()

const { _t } = usei18n()
useWidgetKeys(_t('Hexagon grid'), [
  { combo: ['ArrowLeft'], description: _t('Select previous element') },
  { combo: ['ArrowRight'], description: _t('Select next element') },
  { combo: ['ArrowUp'], description: _t('Select element above') },
  { combo: ['ArrowDown'], description: _t('Select element below') },
  { combo: ['Home'], description: _t('Select first element') },
  { combo: ['End'], description: _t('Select last element') },
  { combo: ['Escape'], description: _t('Hide tooltip') }
])

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

// The one cell with a link and the grid's tab stop. The pointer moves it too, so that its
// click lands on the link.
const current = ref(0)
// Null hides the tooltip; keyboard focus puts it at the cell's centre.
const tooltipPointer = ref<CmkPointerTooltipPointer | null>(null)

watch(
  () => props.cells.length,
  (count) => {
    current.value = Math.min(current.value, Math.max(count - 1, 0))
    if (count === 0) {
      tooltipPointer.value = null
    }
  }
)

const currentBox = computed(() => {
  const layout = grid.value
  const cell = props.cells[current.value]
  const center = layout?.centers[current.value]
  if (layout === null || cell === undefined || center === undefined) {
    return null
  }
  return {
    index: current.value,
    cell,
    name: cell.description ? `${cell.label}, ${cell.description}` : cell.label,
    x: center.x - layout.boxWidth / 2,
    y: center.y - layout.boxHeight / 2,
    width: layout.boxWidth,
    height: layout.boxHeight,
    highlight: hexagonPath(layout.radius, center),
    focus: hexagonPath(layout.radius + FOCUS_OUTLINE_OFFSET, center)
  }
})

function linkCount(cell: HexagonCell): number {
  return contextualLinkCount(cell.links, cell.linkProperties)
}

/** Whether the current host offers several links, which its tooltip then marks. */
const several = computed(() => currentBox.value !== null && linkCount(currentBox.value.cell) > 1)

// While a host's link menu is open, its tooltip stays and the menu opens right below it.
const menuOpen = ref(false)
const tooltip = useTemplateRef<InstanceType<typeof CmkPointerTooltip>>('tooltip')

watch(menuOpen, (open) => {
  if (!open) {
    tooltipPointer.value = null
  }
})

// A refresh can take the menu away, or put another host in its place, without the menu
// reporting that it closed.
const menuHost = computed(() => (several.value ? currentBox.value?.cell.label : undefined))
watch(menuHost, () => {
  menuOpen.value = false
})

const area = useTemplateRef<SVGRectElement>('area')
const linkCell = useTemplateRef<SVGGElement>('linkCell')

function inLinkCell(target: EventTarget | null): boolean {
  return target instanceof Node && (linkCell.value?.contains(target) ?? false)
}

function cellCentre(index: number): CmkPointerTooltipPointer | null {
  const center = grid.value?.centers[index]
  const origin = area.value?.getBoundingClientRect()
  if (center === undefined || origin === undefined) {
    return null
  }
  return { clientX: origin.left + center.x, clientY: origin.top + center.y }
}

// Keeps keyboard focus on the link when it moves to another cell. The link cell is keyed by its
// cell, so focus lands on a new element, which screen readers announce. The old element's blur
// meanwhile does not count as leaving the grid.
let moving = false

async function moveTo(index: number): Promise<void> {
  if (index === current.value) {
    return
  }
  moving = inLinkCell(document.activeElement)
  current.value = index
  if (moving) {
    await nextTick()
    linkCell.value?.querySelector<HTMLElement | SVGElement>('a, [tabindex]')?.focus()
    moving = false
  }
}

function leave(): void {
  if (!menuOpen.value) {
    tooltipPointer.value = null
  }
}

async function track(event: PointerEvent): Promise<void> {
  const layout = grid.value
  const origin = area.value?.getBoundingClientRect()
  if (menuOpen.value || layout === null || origin === undefined) {
    return
  }
  const index = hostIndexAt(layout, event.clientX - origin.left, event.clientY - origin.top)
  if (index === null) {
    tooltipPointer.value = null
    return
  }
  tooltipPointer.value = { clientX: event.clientX, clientY: event.clientY }
  await moveTo(index)
}

// Focus the menu hands back after a click away is no reason to show the tooltip again.
function focusIn(event: FocusEvent): void {
  if (inLinkCell(event.target) && tooltipPointer.value === null && byKeyboard(event)) {
    tooltipPointer.value = cellCentre(current.value)
  }
}

function focusOut(event: FocusEvent): void {
  if (!moving && !menuOpen.value && !inLinkCell(event.relatedTarget)) {
    tooltipPointer.value = null
  }
}

// Captured before a link menu's trigger sees the keys, which would open the menu on ArrowDown.
async function navigate(event: KeyboardEvent): Promise<void> {
  const layout = grid.value
  if (menuOpen.value || layout === null || !inLinkCell(event.target)) {
    return
  }
  if (event.key === 'Escape') {
    tooltipPointer.value = null
    return
  }
  const next = neighbourIndex(layout, current.value, event.key)
  if (next === null) {
    return
  }
  event.preventDefault()
  event.stopPropagation()
  tooltipPointer.value = cellCentre(next)
  await moveTo(next)
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
    <g
      @pointermove="track"
      @pointerleave="leave"
      @keydown.capture="navigate"
      @focusin="focusIn"
      @focusout="focusOut"
    >
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
      <path
        v-if="currentBox && tooltipPointer"
        class="db-hexagon-grid-figure__highlight"
        :d="currentBox.highlight"
        pointer-events="none"
      />
      <g
        v-if="currentBox"
        :key="currentBox.index"
        ref="linkCell"
        class="db-hexagon-grid-figure__link"
      >
        <ContextualLinkTrigger
          v-model:open="menuOpen"
          :links="currentBox.cell.links"
          :link-properties="currentBox.cell.linkProperties"
          :filters="filters"
          :reference="tooltip?.element ?? null"
        >
          <rect
            :x="currentBox.x"
            :y="currentBox.y"
            :width="currentBox.width"
            :height="currentBox.height"
            :aria-label="currentBox.name"
            v-bind="linkCount(currentBox.cell) === 0 ? { tabindex: 0, role: 'img' } : {}"
            fill="transparent"
          />
        </ContextualLinkTrigger>
        <path class="db-hexagon-grid-figure__focus" :d="currentBox.focus" pointer-events="none" />
      </g>
    </g>
  </svg>
  <CmkPointerTooltip ref="tooltip" :pointer="tooltipPointer" @dismiss="leave">
    <slot
      v-if="currentBox && tooltipPointer"
      name="tooltip"
      :index="currentBox.index"
      :several="several"
    />
  </CmkPointerTooltip>
</template>

<style scoped>
.db-hexagon-grid-figure {
  display: block;
}

.db-hexagon-grid-figure__highlight {
  fill: color-mix(in srgb, var(--font-color) 10%, transparent);
}

/* The focused hexagon is outlined, instead of the square box of the link around it. */
.db-hexagon-grid-figure__link > :focus-visible {
  outline: none;
}

.db-hexagon-grid-figure__focus {
  fill: none;
}

.db-hexagon-grid-figure__link > :focus-visible ~ .db-hexagon-grid-figure__focus {
  stroke: var(--font-color);
  stroke-width: 2;
}
</style>
