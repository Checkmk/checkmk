<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a radar map looks like, for the list: a grid of host panels, a few of them
in a problem state. An illustration — a radar map's content comes from a live
filter query the list page does not run.
-->
<script setup lang="ts">
import type { ThumbnailState } from '@/maps/home/components/thumbnails/palette'

interface Panel {
  x: number
  y: number
  state: ThumbnailState
}

/** Four columns, three rows, with the problem states spread over the grid. */
const PANELS: readonly Panel[] = [
  { x: 10, y: 10, state: 'ok' },
  { x: 70, y: 10, state: 'ok' },
  { x: 130, y: 10, state: 'crit' },
  { x: 190, y: 10, state: 'ok' },
  { x: 10, y: 48, state: 'ok' },
  { x: 70, y: 48, state: 'warn' },
  { x: 130, y: 48, state: 'ok' },
  { x: 190, y: 48, state: 'ok' },
  { x: 10, y: 86, state: 'crit' },
  { x: 70, y: 86, state: 'ok' },
  { x: 130, y: 86, state: 'ok' },
  { x: 190, y: 86, state: 'warn' }
]
</script>

<template>
  <svg viewBox="0 0 256 128" class="maps-radar-map-thumbnail">
    <rect width="256" height="128" class="maps-radar-map-thumbnail__canvas" />
    <g
      v-for="(panel, index) in PANELS"
      :key="index"
      class="maps-radar-map-thumbnail__panel"
      :class="`maps-radar-map-thumbnail__panel--${panel.state}`"
    >
      <rect
        :x="panel.x"
        :y="panel.y"
        width="56"
        height="34"
        rx="4"
        class="maps-radar-map-thumbnail__frame"
      />
      <circle :cx="panel.x + 7" :cy="panel.y + 11" r="2.5" class="maps-radar-map-thumbnail__dot" />
      <rect
        :x="panel.x + 13"
        :y="panel.y + 8.5"
        width="30"
        height="3.5"
        rx="1.5"
        class="maps-radar-map-thumbnail__title"
      />
      <rect
        :x="panel.x + 3"
        :y="panel.y + 20"
        width="32"
        height="7"
        rx="2"
        class="maps-radar-map-thumbnail__row"
      />
      <circle
        :cx="panel.x + 7.5"
        :cy="panel.y + 23.5"
        r="1.5"
        class="maps-radar-map-thumbnail__row-dot"
      />
    </g>
  </svg>
</template>

<style scoped>
.maps-radar-map-thumbnail__canvas {
  fill: var(--maps-map-thumbnail-canvas);
}

.maps-radar-map-thumbnail__panel--ok {
  --maps-radar-map-thumbnail-state: var(--maps-map-thumbnail-ok);
}

.maps-radar-map-thumbnail__panel--warn {
  --maps-radar-map-thumbnail-state: var(--maps-map-thumbnail-warn);
}

.maps-radar-map-thumbnail__panel--crit {
  --maps-radar-map-thumbnail-state: var(--maps-map-thumbnail-crit);
}

.maps-radar-map-thumbnail__frame {
  fill: color-mix(in srgb, var(--maps-radar-map-thumbnail-state) 7%, transparent);
  stroke: color-mix(in srgb, var(--maps-radar-map-thumbnail-state) 22%, transparent);
  stroke-width: 0.75;
}

.maps-radar-map-thumbnail__dot,
.maps-radar-map-thumbnail__row-dot {
  fill: var(--maps-radar-map-thumbnail-state);
}

.maps-radar-map-thumbnail__title {
  fill: color-mix(in srgb, var(--maps-radar-map-thumbnail-state) 30%, transparent);
}

.maps-radar-map-thumbnail__row {
  fill: color-mix(in srgb, var(--maps-radar-map-thumbnail-state) 12%, transparent);
}
</style>
