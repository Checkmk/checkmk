<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { fromAbsolute, getLocalTimeZone } from '@internationalized/date'
import { computed, ref, useTemplateRef, watch } from 'vue'

import { isoDate, isoTime, shortWeekday } from '../../../utils/timeFormat'
import type { HoverState } from '../interaction/hover'
import { computeTooltipPosition } from './tooltipPosition'

const CURSOR_OFFSET = 16

const props = defineProps<{
  hoverState: HoverState | null
}>()

const formattedTime = computed(() => {
  if (!props.hoverState) {
    return ''
  }
  const timeZone = getLocalTimeZone()
  const zonedTime = fromAbsolute(props.hoverState.snapTime * 1000, timeZone)
  return `${shortWeekday(props.hoverState.snapTime, timeZone)}, ${isoDate(zonedTime)}  ${isoTime(zonedTime)}`
})

const tooltipElement = useTemplateRef<HTMLDivElement>('tooltip')
const tooltipSize = ref({ width: 0, height: 0 })

// The measured size feeds the position of the same render pass: the post-flush
// watcher runs before the browser paints, so the corrected position is never visible.
watch(
  () => props.hoverState,
  () => {
    tooltipSize.value = {
      width: tooltipElement.value?.offsetWidth ?? 0,
      height: tooltipElement.value?.offsetHeight ?? 0
    }
  },
  { flush: 'post' }
)

const positionStyle = computed(() => {
  if (!props.hoverState) {
    return {}
  }
  const { left, top } = computeTooltipPosition({
    cursorX: props.hoverState.clientX,
    cursorY: props.hoverState.clientY,
    tooltipWidth: tooltipSize.value.width,
    tooltipHeight: tooltipSize.value.height,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    cursorOffset: CURSOR_OFFSET
  })
  return { left: `${left}px`, top: `${top}px` }
})
</script>

<template>
  <!-- Teleported to body because dashboard widget frames are stacking contexts
       (they carry their own z-index), so no z-index inside the widget could keep
       the tooltip above a sibling widget. Unlike a portal rendered by a foreign
       component, our own teleported element keeps its scoped-style attribute. -->
  <Teleport to="body">
    <!-- Pointer-only ephemera (values under the moving cursor), deliberately hidden
         from assistive technology; keyboard users cannot trigger it. -->
    <div
      v-if="hoverState"
      ref="tooltip"
      class="graphing-graph-tooltip"
      :style="positionStyle"
      aria-hidden="true"
    >
      <div class="graphing-graph-tooltip__time">{{ formattedTime }}</div>
      <div class="graphing-graph-tooltip__rows">
        <div
          v-for="sample in hoverState.samples"
          :key="sample.metricName"
          class="graphing-graph-tooltip__row"
          :class="{ 'graphing-graph-tooltip__row--is-closest': sample.isClosest }"
        >
          <span class="graphing-graph-tooltip__swatch" :style="{ background: sample.color }" />
          <span class="graphing-graph-tooltip__label">{{ sample.label }}</span>
          <span class="graphing-graph-tooltip__value">{{ sample.formattedValue }}</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.graphing-graph-tooltip {
  position: fixed;
  z-index: var(--z-index-tooltip-offset);
  min-width: 280px;
  max-width: 420px;
  padding: var(--spacing);
  background: var(--default-tooltip-background-color);
  border: 1px solid var(--default-tooltip-text-color);
  border-radius: var(--border-radius);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-default);
  line-height: normal;
  letter-spacing: 0.36px;
  color: var(--default-tooltip-text-color);
  pointer-events: none;
}

.graphing-graph-tooltip__time {
  margin-bottom: var(--spacing);
  padding: var(--spacing-half) 8px;
  font-variant-numeric: tabular-nums;
}

.graphing-graph-tooltip__rows {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.graphing-graph-tooltip__row {
  display: flex;
  align-items: center;
  gap: var(--spacing);
  padding: var(--spacing-half) 8px;
  border-radius: var(--border-radius);
}

.graphing-graph-tooltip__row--is-closest {
  background: color-mix(in srgb, var(--default-tooltip-text-color) 10%, transparent);
}

.graphing-graph-tooltip__swatch {
  flex: 0 0 auto;
  width: 4px;
  height: 16px;
  border-radius: var(--border-radius-half);
}

.graphing-graph-tooltip__label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-graph-tooltip__value {
  flex: 0 0 auto;
  padding-left: var(--spacing);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
