<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A free-standing block of text on a map — a legend, a note, a heading.

It monitors nothing, so it takes its whole appearance from what the operator
configured, and only falls back to the app's own styling where they configured
nothing.
-->
<script setup lang="ts">
import { renderDateAndTime } from 'cmk-ui-library/lib/renderTime'
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
  const stamp = at ? renderDateAndTime(at) : '—'
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
      classic ? 'maps-map-element-textbox--classic' : '',
      !background ? 'maps-map-element-textbox--surface' : '',
      !object.textbox_border
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
  overflow: auto;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: var(--font-weight-medium);
  color: var(--font-color);
  white-space: pre-wrap;
  pointer-events: none;
  border-radius: var(--border-radius);
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

/* NagVis' .box metrics, so the text fits the width and height NagVis gave the
   box instead of being clipped by Maps' padding and leading. */
.maps-map-element-textbox--classic {
  overflow: visible;
  padding: 0 var(--dimension-2);
  line-height: normal;
}

.maps-map-element-textbox--surface {
  background: var(--maps-map-view-overlay-bg);
}

.maps-map-element-textbox--ring {
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-map-element-textbox--ring-selected {
  box-shadow: 0 0 0 1px var(--interactive-accent);
}
</style>
