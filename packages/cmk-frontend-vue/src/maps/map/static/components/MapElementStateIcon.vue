<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The default icon for a monitored object: a disc in the object's state colour,
carrying a letter for what kind of object it is (or the aggregation glyph).

Drawn as SVG rather than a styled div so the letter centres crisply at any icon
size. The state colour is handed to CSS as a custom property, so the disc, its
glow and the "missing" outline all follow the theme's state tokens.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { stateColorVar } from '@/maps/utils/stateColors'

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
}>()

/** Letter shown for an object kind. */
const TYPE_CHARS: Record<string, string> = {
  host: 'H',
  service: 'S',
  hostgroup: 'HG',
  servicegroup: 'SG',
  dyngroup: 'DG',
  map: 'M',
  image: '◆',
  line: '—',
  aggregation: 'BI'
}

/** States whose colour is loud enough to warrant the heavier glow. */
const STRONG_GLOW_STATES = new Set(['DOWN', 'CRITICAL'])
/** States that carry no glow at all — they say "no data", not "a problem". */
const UNLIT_STATES = new Set(['PENDING', 'NOT_FOUND'])

const stateName = computed(() => props.state?.state ?? 'PENDING')
const missing = computed(() => stateName.value === 'NOT_FOUND')
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

const charFontSize = computed(() => {
  const chars = typeChar.value.length
  const factor = chars === 1 ? 0.44 : chars === 2 ? 0.31 : 0.26
  return Math.max(9, Math.round(props.iconSize * factor))
})

const rootStyle = computed(() => ({
  '--maps-map-element-state-icon-color': stateColorVar(stateName.value)
}))
</script>

<template>
  <svg
    :width="iconSize"
    :height="iconSize"
    :viewBox="`0 0 ${iconSize} ${iconSize}`"
    overflow="visible"
    class="maps-map-element-state-icon"
    :class="{
      'maps-map-element-state-icon--selected': selected,
      'maps-map-element-state-icon--lit': !UNLIT_STATES.has(stateName),
      'maps-map-element-state-icon--lit-strong': STRONG_GLOW_STATES.has(stateName)
    }"
    :style="rootStyle"
  >
    <!-- An object monitoring does not know reads as "missing" rather than as a
         real state: dimmed fill, dashed outline, "?" instead of the type letter. -->
    <circle
      v-if="missing"
      class="maps-map-element-state-icon__disc maps-map-element-state-icon__disc--missing"
      :cx="iconSize / 2"
      :cy="iconSize / 2"
      :r="iconSize / 2 - 1"
      stroke-width="1.5"
      stroke-dasharray="3 2"
    />
    <circle
      v-else
      class="maps-map-element-state-icon__disc"
      :cx="iconSize / 2"
      :cy="iconSize / 2"
      :r="iconSize / 2"
    />
    <g
      v-if="object.type === 'aggregation'"
      class="maps-map-element-state-icon__glyph"
      :stroke-width="Math.max(1, iconSize * 0.06)"
      stroke-linecap="round"
    >
      <line :x1="iconSize / 2" :y1="iconSize * 0.32" :x2="iconSize * 0.32" :y2="iconSize * 0.68" />
      <line :x1="iconSize / 2" :y1="iconSize * 0.32" :x2="iconSize * 0.68" :y2="iconSize * 0.68" />
      <circle :cx="iconSize / 2" :cy="iconSize * 0.32" :r="iconSize * 0.11" />
      <circle :cx="iconSize * 0.32" :cy="iconSize * 0.7" :r="iconSize * 0.1" />
      <circle :cx="iconSize * 0.68" :cy="iconSize * 0.7" :r="iconSize * 0.1" />
    </g>
    <text
      v-else
      class="maps-map-element-state-icon__char"
      :class="missing ? 'maps-map-element-state-icon__char--missing' : ''"
      :x="iconSize / 2"
      :y="iconSize / 2"
      text-anchor="middle"
      dominant-baseline="central"
      :font-size="charFontSize"
      :letter-spacing="typeChar.length > 1 ? -1 : 0.5"
    >
      {{ missing ? '?' : typeChar }}
    </text>
  </svg>
</template>

<style scoped>
.maps-map-element-state-icon {
  display: block;
  border-radius: 9999px;
  user-select: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-map-element-state-icon--lit {
  filter: drop-shadow(
    0 0 5px color-mix(in srgb, var(--maps-map-element-state-icon-color) 55%, transparent)
  );
}

.maps-map-element-state-icon--lit-strong {
  filter: drop-shadow(
    0 0 6px color-mix(in srgb, var(--maps-map-element-state-icon-color) 65%, transparent)
  );
}

.maps-map-element-state-icon--selected {
  box-shadow:
    0 0 0 2px var(--ux-theme-1),
    0 0 0 4px var(--color-corporate-green-50);
}

.maps-map-element-state-icon__disc {
  fill: var(--maps-map-element-state-icon-color);
}

.maps-map-element-state-icon__disc--missing {
  fill: var(--maps-map-view-missing-fill);
  stroke: var(--maps-map-element-state-icon-color);
}

.maps-map-element-state-icon__glyph {
  fill: var(--white);
  stroke: var(--white);
  filter: drop-shadow(0 1px 2px rgb(0 0 0 / 50%));
}

.maps-map-element-state-icon__char {
  font-weight: var(--font-weight-bold);
  fill: var(--white);
  filter: drop-shadow(0 1px 2px rgb(0 0 0 / 50%));
}

.maps-map-element-state-icon__char--missing {
  fill: var(--maps-map-element-state-icon-color);
}
</style>
