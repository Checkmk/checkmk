<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A grid as the editor shows it: a box on its first slot, which is where it is
placed, and a frame around the slots its members take. Outside the editor only
the members are drawn.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject, onMounted, ref, useTemplateRef, watch } from 'vue'

import MapElementResizeHandle from '@/maps/map/elements/components/MapElementResizeHandle.vue'
import { objectIcon } from '@/maps/map/static/composables/useCanvasLineAnchors'
import { CANVAS_SCALE } from '@/maps/map/static/composables/useCanvasViewport'
import { gridExtent } from '@/maps/map/static/gridMembers'
import { gridCaption } from '@/maps/map/static/gridSummary'
import type { MapElement, ObjectState } from '@/maps/types/api'

const i18n = usei18n()
const { _t } = i18n

const props = defineProps<{
  grid: MapElement
  members: MapElement[]
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  focused?: boolean
  /** Shows the grip that sets how many objects a row holds. */
  resizable?: boolean
}>()

const emit = defineEmits<{ 'resize-start': [event: PointerEvent] }>()

const FRAME_PADDING = 'var(--dimension-4)'

const canvasScale = inject(
  CANVAS_SCALE,
  computed(() => ({ sx: 1, sy: 1 }))
)

const extent = computed(() =>
  gridExtent(props.grid, props.members, props.iconSize, canvasScale.value)
)

const box = useTemplateRef<HTMLElement>('box')
const iconShift = ref({ x: 0, y: 0 })

// Measured, not computed: centred with its caption, a member's icon is not on
// its slot, and how tall the caption is is up to the theme.
function measuredIconShift(): { x: number; y: number } {
  const member = props.members[0]
  const canvas = box.value?.closest('.maps-map-canvas')
  if (!member || !canvas) {
    return { x: 0, y: 0 }
  }
  const own = box.value!.getBoundingClientRect()
  const drawn = objectIcon(canvas, member.id)?.getBoundingClientRect()
  if (!drawn || drawn.width === 0) {
    return { x: 0, y: 0 }
  }
  return {
    x: drawn.left - own.left - (member.x - props.grid.x) * canvasScale.value.sx,
    y: drawn.top - own.top - (member.y - props.grid.y) * canvasScale.value.sy
  }
}

function remeasure(): void {
  const shift = measuredIconShift()
  if (shift.x !== iconShift.value.x || shift.y !== iconShift.value.y) {
    iconShift.value = shift
  }
}

// The same for every member, so not again when they move or change places.
watch(
  [
    () => props.grid.label,
    () => props.grid.display,
    () => props.members.length > 0,
    () => props.iconSize,
    canvasScale
  ],
  remeasure,
  { flush: 'post', deep: true }
)
onMounted(remeasure)

// Grows upwards from the frame's bottom edge, so it also takes in the caption
// above, where the selection's toolbar has to go instead.
const extentStyle = computed(() => ({
  left: `calc(-1 * ${FRAME_PADDING})`,
  bottom: `calc(${props.iconSize - extent.value.height}px - ${FRAME_PADDING})`,
  transform: `translate(${iconShift.value.x}px, ${iconShift.value.y}px)`
}))

const frameStyle = computed(() => ({
  width: `calc(${extent.value.width}px + 2 * ${FRAME_PADDING})`,
  height: `calc(${extent.value.height}px + 2 * ${FRAME_PADDING})`
}))

const caption = computed(() => gridCaption(i18n, props.grid, props.state, props.members.length))
</script>

<template>
  <div
    ref="box"
    class="maps-map-grid-frame"
    :style="{ width: `${iconSize}px`, height: `${iconSize}px` }"
  >
    <div class="maps-map-grid-frame__extent" data-object-anchor :style="extentStyle">
      <span class="maps-map-grid-frame__chip">{{ caption }}</span>
      <div
        class="maps-map-grid-frame__frame"
        :class="{
          'maps-map-grid-frame__frame--selected': selected,
          'maps-map-grid-frame__frame--focused': focused,
          'maps-map-grid-frame__frame--failed': state?.stale
        }"
        :style="frameStyle"
      >
        <MapElementResizeHandle
          v-if="resizable"
          horizontal
          :title="_t('Drag to change the objects per row')"
          @start="emit('resize-start', $event)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-map-grid-frame {
  position: relative;
}

.maps-map-grid-frame__extent {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.maps-map-grid-frame__frame {
  position: relative;
  box-sizing: border-box;
  border: 1px dashed var(--font-color-dimmed);
  border-radius: var(--border-radius);
  background: color-mix(in srgb, var(--interactive-accent) 6%, transparent);
}

.maps-map-grid-frame__frame--selected {
  border: 2px solid var(--interactive-accent);
}

/* The browser's own focus ring, which it draws on the focused element only. */
.maps-map-grid-frame__frame--focused {
  outline: auto;
  outline-offset: 2px;
}

.maps-map-grid-frame__frame--failed {
  border-color: var(--color-state-warning);
}

.maps-map-grid-frame__chip {
  pointer-events: auto;
  margin-bottom: var(--dimension-2);
  padding: var(--dimension-1) var(--dimension-3);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
  color: var(--font-color);
  font-size: var(--font-size-small);
  white-space: nowrap;
}
</style>
