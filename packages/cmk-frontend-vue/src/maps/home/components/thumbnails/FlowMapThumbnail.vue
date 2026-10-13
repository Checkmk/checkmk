<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a flow map looks like, for the list: a parent-child tree of hosts. It is an
illustration, not the map's own data — a flow map's nodes come from a live
topology query the list page does not run.
-->
<script setup lang="ts">
import { untranslated } from 'cmk-ui-library/lib/i18n'

import type { ThumbnailState } from '@/maps/home/components/thumbnails/palette'

interface Node {
  x: number
  y: number
  r: number
  state: ThumbnailState
  /** Only the upper tiers are big enough to carry their letter. */
  fontSize?: number
}

const EDGES: readonly [number, number, number, number][] = [
  [128, 28, 72, 66],
  [128, 28, 184, 66],
  [72, 66, 36, 100],
  [72, 66, 108, 100],
  [184, 66, 148, 100],
  [184, 66, 220, 100]
]

const NODES: readonly Node[] = [
  { x: 128, y: 28, r: 11, state: 'ok', fontSize: 7 },
  { x: 72, y: 66, r: 9, state: 'ok', fontSize: 6 },
  { x: 184, y: 66, r: 9, state: 'crit', fontSize: 6 },
  { x: 36, y: 100, r: 7, state: 'ok' },
  { x: 108, y: 100, r: 7, state: 'warn' },
  { x: 148, y: 100, r: 7, state: 'ok' },
  { x: 220, y: 100, r: 7, state: 'ok' }
]
</script>

<template>
  <svg viewBox="0 0 256 128" class="maps-flow-map-thumbnail">
    <rect width="256" height="128" class="maps-flow-map-thumbnail__canvas" />
    <line
      v-for="([x1, y1, x2, y2], index) in EDGES"
      :key="index"
      :x1="x1"
      :y1="y1"
      :x2="x2"
      :y2="y2"
      class="maps-flow-map-thumbnail__edge"
    />
    <template v-for="(node, index) in NODES" :key="index">
      <circle
        :cx="node.x"
        :cy="node.y"
        :r="node.r"
        class="maps-flow-map-thumbnail__node"
        :class="`maps-flow-map-thumbnail__node--${node.state}`"
      />
      <text
        v-if="node.fontSize"
        :x="node.x"
        :y="node.y"
        :style="{ fontSize: `${node.fontSize}px` }"
        text-anchor="middle"
        dominant-baseline="central"
        class="maps-flow-map-thumbnail__label"
      >
        {{ untranslated('H') }}
      </text>
    </template>
  </svg>
</template>

<style scoped>
.maps-flow-map-thumbnail__canvas {
  fill: var(--maps-map-thumbnail-canvas);
}

.maps-flow-map-thumbnail__edge {
  stroke: var(--maps-map-thumbnail-edge);
  stroke-width: 1.5;
}

.maps-flow-map-thumbnail__node--ok {
  fill: var(--maps-map-thumbnail-ok);
}

.maps-flow-map-thumbnail__node--warn {
  fill: var(--maps-map-thumbnail-warn);
}

.maps-flow-map-thumbnail__node--crit {
  fill: var(--maps-map-thumbnail-crit);
}

/* The size is a style declaration rather than a ``font-size`` attribute, and
   the spacing has to be reset: Checkmk's theme carries a
   ``* { font-size: inherit; letter-spacing: … }`` (``_main.scss``), which any
   presentation attribute loses to. */
.maps-flow-map-thumbnail__label {
  fill: var(--maps-map-thumbnail-on-state);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0;
}
</style>
