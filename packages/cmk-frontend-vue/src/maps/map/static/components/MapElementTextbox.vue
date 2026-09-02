<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A free-standing block of text on a map — a legend, a note, a heading.

It monitors nothing, so it takes its whole appearance from what the operator
configured, and only falls back to the app's own styling where they configured
nothing. The classic branch mirrors NagVis' ``.box`` so an imported map keeps
the text sitting where it sat there.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useStates } from '@/maps/services/context'
import type { MapElement } from '@/maps/types/api'

import MapElementResizeHandle from './MapElementResizeHandle.vue'

/** ``LabelConfig.color``'s default; anything else is a deliberate choice. */
const DEFAULT_LABEL_COLORS = new Set(['#ffffff', '#FFFFFF'])

/** Legacy NagVis macro for when monitoring data was last fetched. */
const LAST_RUN_MACRO = '[worker_last_run]'

const props = defineProps<{
  object: MapElement
  selected?: boolean
  editMode?: boolean
  /** Live size while the operator is dragging the resize grip. */
  resizeOverride?: { width: number; height: number } | undefined
  /** The NagVis-compatible renderer. */
  classic?: boolean
}>()

defineEmits<{ 'resize-start': [event: PointerEvent] }>()

const states = useStates()

const text = computed(() => {
  const raw = props.object.label?.text || 'Text'
  if (!raw.includes(LAST_RUN_MACRO)) {
    return raw
  }
  const at = states.lastUpdate.value
  const stamp = at ? new Date(at * 1000).toLocaleString('sv-SE').replace('T', ' ') : '—'
  return raw.replaceAll(LAST_RUN_MACRO, stamp)
})

const background = computed(() => {
  const configured = props.object.textbox_background
  return configured && configured !== 'transparent' ? configured : null
})

const configuredStyle = computed(() => {
  const label = props.object.label
  const width = props.resizeOverride?.width ?? props.object.textbox_width
  const height = props.resizeOverride?.height ?? props.object.textbox_height
  const color = label?.color && !DEFAULT_LABEL_COLORS.has(label.color) ? label.color : undefined
  return {
    background: background.value ?? undefined,
    // borderColor alone paints nothing without a width and a style.
    border: props.object.textbox_border ? `1px solid ${props.object.textbox_border}` : undefined,
    color,
    fontSize: label?.size ? `${label.size}px` : undefined,
    fontWeight: label?.weight ?? undefined,
    textAlign: label?.align ?? undefined,
    width: width ? `${width}px` : undefined,
    height: height ? `${height}px` : undefined
  }
})
</script>

<template>
  <div
    class="maps-map-element-textbox"
    :class="[
      classic ? 'maps-map-element-textbox--classic' : 'maps-map-element-textbox--boxed',
      // Blurring an opaque imported background turns it into a frosted smear.
      !classic && !background ? 'maps-map-element-textbox--glass' : '',
      !classic && !object.textbox_border
        ? selected
          ? 'maps-map-element-textbox--ring-selected'
          : 'maps-map-element-textbox--ring'
        : ''
    ]"
    :style="configuredStyle"
  >
    {{ text }}
    <MapElementResizeHandle v-if="editMode" @start="$emit('resize-start', $event)" />
  </div>
</template>

<style scoped>
.maps-map-element-textbox {
  position: relative;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  white-space: pre-wrap;
  pointer-events: none;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

/* NagVis' .box: content-box sizing, 2px of side padding and a natural line
   height, so the text fills the box and sits as centred as it does there
   instead of being pushed down by a tall leading. */
.maps-map-element-textbox--classic {
  overflow: visible;
  box-sizing: content-box;
  padding: 0 2px;
  line-height: normal;
  color: var(--maps-map-view-classic-ink);
  background: transparent;
  border-radius: 0;
}

.maps-map-element-textbox--boxed {
  overflow: auto;
  padding: 6px 10px;
  color: var(--font-color);
  border-radius: 8px;
}

.maps-map-element-textbox--glass {
  background: var(--maps-map-view-glass);
  backdrop-filter: blur(4px);
}

.maps-map-element-textbox--ring {
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-map-element-textbox--ring-selected {
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}
</style>
