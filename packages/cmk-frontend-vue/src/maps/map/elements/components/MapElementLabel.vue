<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The caption under (or beside) a map object.

Every object type that shows a name shows it through this component, so the
placement quirks of the NagVis-compatible renderer live in one place. Only what
the operator configured per object — colour, background, border, size, width,
offset — is applied inline; the rest is this component's own styling.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { MapElement } from '@/maps/types/api'

const props = defineProps<{
  object: MapElement
  text: string
  /**
   * ``stacked`` sits in the object's flex column, ``caption`` is pinned below a
   * sized object (a graph or a text box), and ``plain`` is placed by whoever
   * renders it — a geo map's line label sits on a Leaflet marker.
   */
  placement: 'stacked' | 'caption' | 'plain'
  /** The NagVis-compatible renderer, which pins the label absolutely. */
  classic?: boolean
}>()

/**
 * Where the label sits. The classic renderer treats ``label_y`` as the
 * absolute offset from the object's anchor rather than as a delta on top of an
 * already-stacked layout, so it positions rather than translates. As in NagVis,
 * a left-aligned label starts ``x`` from the object's left edge, any other one
 * is centered on the object.
 */
const position = computed(() => {
  const x = props.object.label?.x ?? 0
  const y = props.object.label?.y ?? 0
  if (props.classic) {
    return props.object.label?.align === 'left'
      ? { left: `${x}px`, top: `${y}px` }
      : { left: '50%', top: `${y}px`, transform: `translateX(calc(-50% + ${x}px))` }
  }
  return { transform: x || y ? `translate(${x}px, ${y}px)` : undefined }
})

const configuredStyle = computed(() => {
  const label = props.object.label
  const background = label?.background
  const width = label?.width
  return {
    fontSize: `${label?.size ?? 11}px`,
    color: label?.color ?? undefined,
    background: background && background !== 'transparent' ? background : undefined,
    width: width ? `${width}px` : undefined,
    whiteSpace: width ? 'normal' : undefined,
    wordBreak: width ? ('break-word' as const) : undefined,
    // An outline, so a border does not grow the layout the label sits in.
    outline: props.object.label_border ? `1px solid ${props.object.label_border}` : undefined,
    ...position.value
  }
})
</script>

<template>
  <div
    class="maps-map-element-label"
    :class="[`maps-map-element-label--${placement}`, { 'maps-map-element-label--pinned': classic }]"
    :style="configuredStyle"
  >
    {{ text }}
  </div>
</template>

<style scoped>
.maps-map-element-label {
  font-weight: var(--font-weight-medium);
  color: var(--maps-map-view-label-ink);
  white-space: nowrap;
  pointer-events: none;
  background: var(--maps-map-view-label-bg);
  outline: 1px solid var(--border-color-hairline);
  text-shadow: var(--maps-map-view-text-halo);
}

.maps-map-element-label--stacked,
.maps-map-element-label--plain {
  padding: var(--dimension-2) var(--dimension-4);
  border-radius: var(--border-radius);
}

.maps-map-element-label--stacked {
  margin-top: var(--dimension-4);
}

/* Placed at the label's own offset from the object, not after the icon. */
.maps-map-element-label--pinned {
  position: absolute;
  margin-top: 0;
}

.maps-map-element-label--caption {
  position: absolute;
  right: 0;
  bottom: -20px;
  left: 0;
  padding: var(--dimension-2) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  text-align: center;
  border-radius: var(--border-radius);
}
</style>
