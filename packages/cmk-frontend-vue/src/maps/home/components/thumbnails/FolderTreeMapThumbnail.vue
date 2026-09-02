<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a folder-tree map looks like, for the list: nested Checkmk folders with the
worst state of each folder at the right. An illustration — the real tree is
built by the daemon from the site's folder hierarchy.
-->
<script setup lang="ts">
import type { ThumbnailState } from '@/maps/home/components/thumbnails/palette'

interface Row {
  /** Left edge of the folder glyph; the indent that shows the nesting. */
  x: number
  y: number
  /** Width of the folder-name bar. */
  width: number
  state: ThumbnailState
  /** Leaf rows carry no expander, and their name reads dimmer. */
  expander?: string
  dim?: boolean
}

/** The connector lines between the expanders. */
const CONNECTORS = 'M16 24 V102 M16 39 H26 M16 102 H26 M32 45 V81 M32 60 H42 M32 81 H42'

const ROWS: readonly Row[] = [
  { x: 22, y: 12, width: 78, state: 'ok', expander: 'M10.5 15.5 h6 l-3 5 z' },
  { x: 38, y: 33, width: 66, state: 'crit', expander: 'M26.5 36.5 h6 l-3 5 z' },
  { x: 44, y: 54, width: 54, state: 'crit', dim: true },
  { x: 44, y: 75, width: 60, state: 'ok', dim: true },
  { x: 38, y: 96, width: 70, state: 'warn', expander: 'M27 99 l4 3 l-4 3 z' }
]
</script>

<template>
  <svg viewBox="0 0 256 128" class="maps-folder-tree-map-thumbnail">
    <rect width="256" height="128" class="maps-folder-tree-map-thumbnail__canvas" />
    <path :d="CONNECTORS" class="maps-folder-tree-map-thumbnail__connectors" />
    <g
      v-for="(row, index) in ROWS"
      :key="index"
      class="maps-folder-tree-map-thumbnail__row"
      :class="`maps-folder-tree-map-thumbnail__row--${row.state}`"
    >
      <path
        v-if="row.expander"
        :d="row.expander"
        class="maps-folder-tree-map-thumbnail__expander"
      />
      <rect
        :x="row.x"
        :y="row.y"
        width="6"
        height="3"
        rx="1"
        class="maps-folder-tree-map-thumbnail__tab"
      />
      <rect
        :x="row.x"
        :y="row.y + 2"
        width="14"
        height="9"
        rx="1.5"
        class="maps-folder-tree-map-thumbnail__folder"
      />
      <rect
        :x="row.x + 18"
        :y="row.y + 4"
        :width="row.width"
        height="5"
        rx="2"
        class="maps-folder-tree-map-thumbnail__name"
        :class="row.dim ? 'maps-folder-tree-map-thumbnail__name--dim' : ''"
      />
      <circle cx="240" :cy="row.y + 6" r="3.5" class="maps-folder-tree-map-thumbnail__state" />
    </g>
  </svg>
</template>

<style scoped>
.maps-folder-tree-map-thumbnail__canvas {
  fill: var(--maps-map-thumbnail-canvas);
}

.maps-folder-tree-map-thumbnail__connectors {
  fill: none;
  stroke: var(--maps-map-thumbnail-edge);
  stroke-width: 1;
}

.maps-folder-tree-map-thumbnail__row--ok {
  --maps-folder-tree-map-thumbnail-state: var(--maps-map-thumbnail-ok);
}

.maps-folder-tree-map-thumbnail__row--warn {
  --maps-folder-tree-map-thumbnail-state: var(--maps-map-thumbnail-warn);
}

.maps-folder-tree-map-thumbnail__row--crit {
  --maps-folder-tree-map-thumbnail-state: var(--maps-map-thumbnail-crit);
}

.maps-folder-tree-map-thumbnail__expander {
  fill: var(--maps-map-thumbnail-neutral);
}

.maps-folder-tree-map-thumbnail__tab {
  fill: color-mix(in srgb, var(--maps-folder-tree-map-thumbnail-state) 50%, transparent);
}

.maps-folder-tree-map-thumbnail__folder {
  fill: color-mix(in srgb, var(--maps-folder-tree-map-thumbnail-state) 18%, transparent);
  stroke: color-mix(in srgb, var(--maps-folder-tree-map-thumbnail-state) 60%, transparent);
  stroke-width: 0.75;
}

.maps-folder-tree-map-thumbnail__name {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 22%, transparent);
}

.maps-folder-tree-map-thumbnail__name--dim {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 16%, transparent);
}

.maps-folder-tree-map-thumbnail__state {
  fill: var(--maps-folder-tree-map-thumbnail-state);
}
</style>
