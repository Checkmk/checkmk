<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computeTooltipPosition } from 'cmk-ui-library/lib/tooltipPosition'
import { computed, onScopeDispose, ref, useTemplateRef, watch } from 'vue'

export interface CmkPointerTooltipPointer {
  clientX: number
  clientY: number
}

const CURSOR_OFFSET_X = 19
const CURSOR_OFFSET_Y = 8

const props = defineProps<{
  pointer: CmkPointerTooltipPointer | null
}>()

const emit = defineEmits<{ dismiss: [] }>()

const tooltipElement = useTemplateRef<HTMLDivElement>('tooltip')
const tooltipSize = ref({ width: 0, height: 0 })

// The post-flush watcher runs before the browser paints, so the corrected position is never
// visible.
watch(
  [() => props.pointer, tooltipElement],
  () => {
    const tooltip = tooltipElement.value
    if (!tooltip) {
      tooltipSize.value = { width: 0, height: 0 }
      return
    }
    if (!tooltip.matches(':popover-open')) {
      tooltip.showPopover()
    }
    tooltipSize.value = { width: tooltip.offsetWidth, height: tooltip.offsetHeight }
  },
  { flush: 'post' }
)

const positionStyle = computed(() => {
  if (!props.pointer) {
    return {}
  }
  const { left, top } = computeTooltipPosition({
    cursorX: props.pointer.clientX,
    cursorY: props.pointer.clientY,
    tooltipWidth: tooltipSize.value.width,
    tooltipHeight: tooltipSize.value.height,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    cursorOffsetX: CURSOR_OFFSET_X,
    cursorOffsetY: CURSOR_OFFSET_Y
  })
  return { left: `${left}px`, top: `${top}px` }
})

function dismiss(): void {
  if (props.pointer) {
    emit('dismiss')
  }
}

window.addEventListener('scroll', dismiss, { capture: true, passive: true })
window.addEventListener('resize', dismiss, { passive: true })
onScopeDispose(() => {
  window.removeEventListener('scroll', dismiss, { capture: true })
  window.removeEventListener('resize', dismiss)
})
</script>

<template>
  <!-- On the body: a dashboard widget frame is a stacking context, so no z-index inside it could
       keep the tooltip above a neighbouring widget. -->
  <Teleport to="body">
    <!-- Pointer-only, so hidden from assistive technology; keyboard users cannot open it. -->
    <div
      v-if="pointer"
      ref="tooltip"
      class="cmk-pointer-tooltip"
      popover="manual"
      :style="positionStyle"
      aria-hidden="true"
    >
      <slot />
    </div>
  </Teleport>
</template>

<style scoped>
.cmk-pointer-tooltip {
  position: fixed;
  inset: auto;
  margin: 0;
  overflow: visible;
  padding: var(--dimension-5);
  background: var(--ux-theme-2);
  border: 1px solid var(--font-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  line-height: normal;
  letter-spacing: 0.36px;
  color: var(--font-color);
  pointer-events: none;
}
</style>
