<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The corner grip that resizes a sized object (a graph or a text box) in edit
mode; ``horizontal``, it is the one that sets a grid's objects per row. It
only reports the gesture's start; the canvas tracks the pointer, because the
drag has to keep working once the pointer leaves this handle.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{ horizontal?: boolean; title?: string }>()

defineEmits<{ start: [event: PointerEvent] }>()
</script>

<template>
  <div
    class="maps-map-element-resize-handle"
    :class="{ 'maps-map-element-resize-handle--horizontal': horizontal }"
    :title="title ?? _t('Resize')"
    @pointerdown.stop="$emit('start', $event)"
  >
    <svg
      class="maps-map-element-resize-handle__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path
        v-if="horizontal"
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M3.5 12h17M7.5 8l-4 4 4 4M16.5 8l4 4-4 4"
      />
      <path
        v-else
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M4.5 19.5l15-15M19.5 4.5v6m0-6h-6"
      />
    </svg>
  </div>
</template>

<style scoped>
.maps-map-element-resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-7);
  height: var(--dimension-7);
  background: color-mix(in srgb, var(--interactive-accent) 70%, transparent);
  border-top-left-radius: var(--border-radius);
  cursor: se-resize;
  transition: background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-map-element-resize-handle--horizontal {
  cursor: ew-resize;
}

.maps-map-element-resize-handle:hover {
  background: var(--interactive-accent);
}

.maps-map-element-resize-handle__icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
  color: var(--white);
}
</style>
