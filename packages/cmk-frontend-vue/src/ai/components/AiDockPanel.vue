<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkResizeHandle from 'cmk-ui-library/components/CmkResizeHandle.vue'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, onMounted, ref, useId, useTemplateRef, watch } from 'vue'

export type AiDockPanelDock = 'left' | 'right' | 'bottom'

export interface AiDockPanelProps {
  dock?: AiDockPanelDock
  minSize: number
}

const KEYBOARD_RESIZE_STEP = 50

const { dock = 'right', minSize } = defineProps<AiDockPanelProps>()

const size = defineModel<number>('size', { required: true })
const collapsed = defineModel<boolean>('collapsed', { default: false })

const root = useTemplateRef('root')
const contentId = useId()

const vertical = computed(() => dock === 'bottom')
const containerSize = ref(Infinity)

function setContainerSize(): void {
  const element = root.value
  const container = element?.offsetParent
  if (!element || !container) {
    return
  }
  const rect = container.getBoundingClientRect()
  const border = vertical.value
    ? element.offsetHeight - element.clientHeight
    : element.offsetWidth - element.clientWidth
  const extent = (vertical.value ? rect.height : rect.width) - border
  containerSize.value = extent > 0 ? extent : Infinity
}

const { observe } = useResizeObserver(setContainerSize)
observe(computed(() => root.value?.offsetParent ?? null))

onMounted(setContainerSize)
watch(() => dock, setContainerSize, { flush: 'post' })

const effectiveMaxSize = computed(() => Math.max(minSize, containerSize.value))

function clamp(value: number): number {
  return Math.min(effectiveMaxSize.value, Math.max(minSize, value))
}

watch(
  [size, () => minSize, effectiveMaxSize],
  () => {
    const clamped = clamp(size.value)
    if (clamped !== size.value) {
      size.value = clamped
    }
  },
  { immediate: true }
)

function resizeTo(value: number): void {
  if (value < minSize / 2) {
    collapsed.value = true
    return
  }
  collapsed.value = false
  size.value = clamp(value)
}

const growKey = computed(
  () => ({ left: 'ArrowRight', right: 'ArrowLeft', bottom: 'ArrowUp' })[dock]
)
const shrinkKey = computed(
  () => ({ left: 'ArrowLeft', right: 'ArrowRight', bottom: 'ArrowDown' })[dock]
)

function onKeydown(event: KeyboardEvent): void {
  const current = collapsed.value ? 0 : size.value
  switch (event.key) {
    case growKey.value:
      resizeTo(Math.max(minSize, current + KEYBOARD_RESIZE_STEP))
      break
    case shrinkKey.value:
      resizeTo(current - KEYBOARD_RESIZE_STEP)
      break
    case 'Enter':
      collapsed.value = !collapsed.value
      break
    default:
      return
  }
  event.preventDefault()
}

interface Drag {
  pointerId: number
  start: number
  startSize: number
}

let drag: Drag | null = null

function pointerPosition(event: PointerEvent): number {
  return vertical.value ? event.clientY : event.clientX
}

function onPointerdown(event: PointerEvent): void {
  if (event.button !== 0) {
    return
  }
  event.preventDefault()
  const handle = event.currentTarget as HTMLElement
  handle.focus()
  handle.setPointerCapture?.(event.pointerId)
  drag = {
    pointerId: event.pointerId,
    start: pointerPosition(event),
    startSize: collapsed.value ? 0 : size.value
  }
}

function onPointermove(event: PointerEvent): void {
  if (drag?.pointerId !== event.pointerId) {
    return
  }
  const moved = pointerPosition(event) - drag.start
  const grownBy = dock === 'left' ? moved : -moved
  resizeTo(drag.startSize + grownBy)
}

function endDrag(event: PointerEvent): void {
  if (drag?.pointerId !== event.pointerId) {
    return
  }
  drag = null
}

const rootStyle = computed(() => ({
  [vertical.value ? 'height' : 'width']: `calc(${size.value}px + var(--dimension-2))`,
  display: collapsed.value ? 'none' : undefined
}))
</script>

<template>
  <div ref="root" class="ai-dock-panel" :class="`ai-dock-panel--${dock}`" :style="rootStyle">
    <div :id="contentId" class="ai-dock-panel__content">
      <slot />
    </div>
    <div
      class="ai-dock-panel__handle"
      role="separator"
      tabindex="0"
      :aria-orientation="vertical ? 'horizontal' : 'vertical'"
      :aria-controls="contentId"
      :aria-valuenow="collapsed ? 0 : size"
      :aria-valuemin="0"
      :aria-valuemax="effectiveMaxSize"
      @pointerdown="onPointerdown"
      @pointermove="onPointermove"
      @pointerup="endDrag"
      @pointercancel="endDrag"
      @lostpointercapture="endDrag"
      @keydown="onKeydown"
    >
      <CmkResizeHandle :orientation="vertical ? 'horizontal' : 'vertical'" />
    </div>
  </div>
</template>

<style scoped>
.ai-dock-panel {
  --ai-dock-panel-border-width: var(--dimension-2);
  --ai-dock-panel-handle-offset: calc((var(--ai-dock-panel-border-width) - var(--dimension-6)) / 2);

  position: absolute;
  display: flex;
  box-sizing: border-box;
  border: 0 solid var(--border-color-subtle);
}

.ai-dock-panel--right {
  top: 0;
  right: 0;
  bottom: 0;
  border-left-width: var(--ai-dock-panel-border-width);
}

.ai-dock-panel--left {
  top: 0;
  bottom: 0;
  left: 0;
  border-right-width: var(--ai-dock-panel-border-width);
}

.ai-dock-panel--bottom {
  right: 0;
  bottom: 0;
  left: 0;
  border-top-width: var(--ai-dock-panel-border-width);
}

.ai-dock-panel:has(> .ai-dock-panel__handle:hover),
.ai-dock-panel:has(> .ai-dock-panel__handle:active) {
  border-color: var(--interactive-neutral);
}

.ai-dock-panel__content {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.ai-dock-panel__handle {
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 0;
  bottom: 0;
  width: var(--dimension-6);
  cursor: col-resize;
  outline: none;
  touch-action: none;
}

.ai-dock-panel--right > .ai-dock-panel__handle {
  left: calc(var(--ai-dock-panel-handle-offset) - var(--ai-dock-panel-border-width));
}

.ai-dock-panel--left > .ai-dock-panel__handle {
  right: calc(var(--ai-dock-panel-handle-offset) - var(--ai-dock-panel-border-width));
}

.ai-dock-panel--bottom > .ai-dock-panel__handle {
  inset: calc(var(--ai-dock-panel-handle-offset) - var(--ai-dock-panel-border-width)) 0 auto;
  width: auto;
  height: var(--dimension-6);
  cursor: row-resize;
}

.ai-dock-panel__handle:focus-visible {
  outline: 1px solid var(--success);
}
</style>
