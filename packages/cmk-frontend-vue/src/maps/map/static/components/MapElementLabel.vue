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
   * sized object (a graph or a text box).
   */
  placement: 'stacked' | 'caption'
  /** The NagVis-compatible renderer, which pins the label absolutely. */
  classic?: boolean
}>()

/**
 * Where the label sits. The classic renderer treats ``label_y`` as the
 * absolute offset from the object's anchor rather than as a delta on top of an
 * already-stacked layout, so it positions rather than translates.
 */
const position = computed(() => {
  const x = props.object.label?.x ?? 0
  const y = props.object.label?.y ?? 0
  if (props.classic) {
    return {
      position: 'absolute' as const,
      left: '50%',
      top: `${y}px`,
      transform: `translateX(calc(-50% + ${x}px))`
    }
  }
  return { transform: x || y ? `translate(${x}px, ${y}px)` : undefined }
})

/**
 * The classic renderer mirrors NagVis' ``.box`` border, which is an actual
 * element border so the rendered line lands where NagVis draws it; the default
 * renderer uses an outline, which does not grow the flex layout it lives in.
 */
const border = computed(() => {
  const configured = props.object.label_border
  if (!configured) {
    return {}
  }
  return props.classic
    ? { border: `1px solid ${configured}`, padding: '0 2px' }
    : { outline: `1px solid ${configured}` }
})

const configuredStyle = computed(() => {
  const label = props.object.label
  const background = label?.background
  const width = label?.width
  return {
    fontSize: `${label?.size ?? 11}px`,
    color: label?.color ?? undefined,
    background: background && background !== 'transparent' ? background : undefined,
    // NagVis' label_width caps the width but only wraps on whitespace, so a
    // single token ("SW01") overflows rather than splitting mid-word.
    width: width ? `${width}px` : undefined,
    whiteSpace: width ? (props.classic ? 'nowrap' : 'normal') : undefined,
    wordBreak: width && !props.classic ? ('break-word' as const) : undefined,
    ...border.value,
    ...position.value
  }
})
</script>

<template>
  <div
    class="maps-map-element-label"
    :class="[
      `maps-map-element-label--${placement}`,
      classic ? 'maps-map-element-label--classic' : 'maps-map-element-label--boxed'
    ]"
    :style="configuredStyle"
  >
    {{ text }}
  </div>
</template>

<style scoped>
.maps-map-element-label {
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
}

.maps-map-element-label--boxed {
  color: var(--maps-map-view-label-ink);
  background: var(--maps-map-view-label-bg);
  outline: 1px solid var(--maps-map-view-hairline);
  backdrop-filter: blur(4px);
  text-shadow: var(--maps-map-view-text-halo);
}

/* Classic tightens the line box to NagVis' span so the label keeps the same
   height and does not overhang its container. */
.maps-map-element-label--classic {
  line-height: 1.2;
  color: var(--maps-map-view-classic-ink);
  background: transparent;
  backdrop-filter: none;
  text-shadow: none;
}

.maps-map-element-label--stacked.maps-map-element-label--boxed {
  margin-top: 6px;
  padding: var(--dimension-2) 6px;
  border-radius: var(--border-radius);
}

.maps-map-element-label--caption {
  position: absolute;
  right: 0;
  bottom: -20px;
  left: 0;
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  text-align: center;
  border-radius: var(--border-radius);
}
</style>
